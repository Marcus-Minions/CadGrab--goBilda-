import adsk.core, adsk.fusion, adsk.cam, traceback
import os, sys, zipfile, tempfile
from urllib.parse import urlparse, urljoin, quote
import urllib.request
import ssl

sys.path.append(os.path.join(os.path.dirname(__file__), 'libraries'))

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

handlers = []

def run(context):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        folder_path = os.path.dirname(__file__)
        resource_folder = os.path.join(folder_path, 'resources')

        cmd_definitions = ui.commandDefinitions
        cmd_def = cmd_definitions.itemById('FusionFTCImporter')
        if not cmd_def:
            cmd_def = cmd_definitions.addButtonDefinition(
                'FusionFTCImporter',
                'Import a STEP File',
                'Imports a STEP file from a given Product Page URL',
                resource_folder
            )

        workspace = ui.workspaces.itemById('FusionSolidEnvironment')
        panel = workspace.toolbarPanels.itemById('InsertPanel')
        control = panel.controls.itemById('FusionFTCImporter')
        if not control:
            panel.controls.addCommand(cmd_def)

        on_command_created = ImportCommandCreatedHandler()
        cmd_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created)

    except Exception:
        adsk.core.Application.get().userInterface.messageBox(f'Add-in start failed:\n{traceback.format_exc()}')

def stop(context):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        panel = ui.workspaces.itemById('FusionSolidEnvironment').toolbarPanels.itemById('InsertPanel')
        control = panel.controls.itemById('FusionFTCImporter')
        if control:
            control.deleteMe()

        cmd_def = ui.commandDefinitions.itemById('FusionFTCImporter')
        if cmd_def:
            cmd_def.deleteMe()

    except Exception:
        adsk.core.Application.get().userInterface.messageBox(f'Add-in stop failed:\n{traceback.format_exc()}')

class ImportCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            
            inputs.addTextBoxCommandInput('url_input', 'Product Page URL', '', 1, False)

      
            inputs.addBoolValueInput('saveToCloud', 'Save to Cloud?', True, '', False)

            on_execute = ImportCommandExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)

        except Exception:
            adsk.core.Application.get().userInterface.messageBox(f'Command creation failed:\n{traceback.format_exc()}')



def safe_download(url, local_path):
    """Download a file with proper SSL handling and error management"""
    try:

        if not url or not url.startswith(('http://', 'https://')):
            return False, f"Invalid URL: {url}"
        

        parsed = urlparse(url)

        encoded_path = quote(parsed.path, safe='/')

        encoded_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
        if parsed.query:
            encoded_url += f"?{parsed.query}"
        if parsed.fragment:
            encoded_url += f"#{parsed.fragment}"
        

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        

        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')]
        urllib.request.install_opener(opener)
        

        urllib.request.urlretrieve(encoded_url, local_path)

        if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
            return False, "Downloaded file is empty or doesn't exist"
        
        return True, None
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Download failed: {str(e)}"

def extract_all_steps_from_zip(zip_path, extract_dir):
    extracted_paths = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        for member in zip_ref.namelist():
            if member.lower().endswith(('.step', '.stp')) and not member.endswith('/'):
                extracted_paths.append(os.path.join(extract_dir, member))
            elif member.lower().endswith('.zip') and not member.endswith('/'):
                nested_zip_path = os.path.join(extract_dir, member)
                zip_ref.extract(member, extract_dir)
                inner_extract_dir = os.path.join(extract_dir, os.path.splitext(member)[0])
                os.makedirs(inner_extract_dir, exist_ok=True)
                extracted_paths.extend(extract_all_steps_from_zip(nested_zip_path, inner_extract_dir))
    return extracted_paths

class ImportCommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        ui = None
        driver = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface

            inputs = args.command.commandInputs
            product_url = inputs.itemById('url_input').text.strip()
            save_to_cloud = inputs.itemById('saveToCloud').value

            if not product_url or not product_url.startswith('http'):
                ui.messageBox("Invalid URL. Please enter a valid product page URL.")
                return

            step_links = []
            zip_link = None

            def collect_step_links(html):
                nonlocal zip_link
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href'].lower()
                    full_url = urljoin(product_url, a['href'])
                    if '.step' in href or '.stp' in href:
                        step_links.append(full_url)
                    elif '.zip' in href and not zip_link:
                        zip_link = full_url


            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')

                driver = webdriver.Chrome(options=chrome_options)
                driver.get(product_url)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//a[contains(@href, ".STEP") or contains(@href, ".zip") or contains(@href, ".stp")]'))
                )
                collect_step_links(driver.page_source)
            finally:
                if driver:
                    driver.quit()
                    driver = None

            temp_dir = tempfile.mkdtemp()
            chosen_path = None

            if step_links:
                display_names = [os.path.basename(urlparse(link).path) for link in step_links]
                choice_input = ui.inputBox(
                    "Multiple STEP files found.\nSelect file number:\n\n" +
                    "\n".join(f"{i+1}. {name}" for i, name in enumerate(display_names)),
                    "Choose STEP File", "1"
                )

                if isinstance(choice_input, list):
                    choice_input = choice_input[0]

                try:
                    index = int(choice_input) - 1
                    if 0 <= index < len(step_links):
                        chosen_link = step_links[index]
                    else:
                        ui.messageBox("Invalid selection. Aborting.")
                        return
                except Exception:
                    ui.messageBox("Invalid input. Aborting.")
                    return

                filename = os.path.basename(urlparse(chosen_link).path)
                chosen_path = os.path.join(temp_dir, filename)
                

                success, error_msg = safe_download(chosen_link, chosen_path)
                if not success:
                    ui.messageBox(f"Failed to download STEP file: {error_msg}\nURL: {chosen_link}")
                    return

            elif zip_link:
                zip_path = os.path.join(temp_dir, 'part.zip')
                

                success, error_msg = safe_download(zip_link, zip_path)
                if not success:
                    ui.messageBox(f"Failed to download ZIP file: {error_msg}\nURL: {zip_link}")
                    return

                step_paths = extract_all_steps_from_zip(zip_path, temp_dir)

                if not step_paths:
                    ui.messageBox("No STEP files found in ZIP.")
                    return

                chosen_path = step_paths[0]
                if len(step_paths) > 1:
                    display_names = [os.path.basename(p) for p in step_paths]
                    choice_input = ui.inputBox(
                        "Multiple STEP files found in ZIP.\nSelect file number:\n\n" +
                        "\n".join(f"{i+1}. {name}" for i, name in enumerate(display_names)),
                        "Choose STEP File", "1"
                    )

                    if isinstance(choice_input, list):
                        choice_input = choice_input[0]

                    try:
                        index = int(choice_input) - 1
                        if 0 <= index < len(step_paths):
                            chosen_path = step_paths[index]
                        else:
                            ui.messageBox("Invalid selection. Aborting.")
                            return
                    except Exception:
                        ui.messageBox("Invalid input. Aborting.")
                        return
            else:
                ui.messageBox("No STEP or ZIP file found.")
                return

            if save_to_cloud:
                current_doc = app.activeDocument
                originalDesign = adsk.fusion.Design.cast(current_doc.products.itemByProductType('DesignProductType'))

                new_doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
                new_design = adsk.fusion.Design.cast(new_doc.products.itemByProductType('DesignProductType'))
                if not new_design:
                    ui.messageBox("Could not create new design document.")
                    return

                import_mgr = app.importManager
                step_options = import_mgr.createSTEPImportOptions(chosen_path)
                import_mgr.importToTarget(step_options, new_design.rootComponent)

                data = app.data
                projects = data.dataProjects
                project_names = [projects.item(i).name for i in range(projects.count)]

                project_choice_input = ui.inputBox(
                    "Select a project number to save the STEP file to:\n\n" +
                    "\n".join(f"{i+1}. {name}" for i, name in enumerate(project_names)),
                    "Choose Fusion Team Project",
                    "1"
                )

                if isinstance(project_choice_input, list):
                    project_choice_input = project_choice_input[0]

                try:
                    project_index = int(project_choice_input) - 1
                    if 0 <= project_index < len(project_names):
                        selected_project = projects.item(project_index)
                    else:
                        ui.messageBox("Invalid project selection. Aborting.")
                        return
                except Exception:
                    ui.messageBox("Invalid input. Aborting.")
                    return

            
                root_folder = selected_project.rootFolder
                all_folders = [(root_folder, 0)]
                for i in range(root_folder.dataFolders.count):
                    all_folders.append((root_folder.dataFolders.item(i), 1))

                folder_choices = [
                    f"{i+1}. {'  ' * depth}{fld.name}"
                    for i, (fld, depth) in enumerate(all_folders)
                ]

                folder_choice_input = ui.inputBox(
                    "Select a folder number to save the STEP file into:\n\n" + "\n".join(folder_choices),
                    "Choose Folder in Project",
                    "1"
                )

                if isinstance(folder_choice_input, list):
                    folder_choice_input = folder_choice_input[0]

                try:
                    folder_index = int(folder_choice_input) - 1
                    if 0 <= folder_index < len(all_folders):
                        selected_folder = all_folders[folder_index][0]
                    else:
                        ui.messageBox("Invalid folder selection. Aborting.")
                        return
                except Exception:
                    ui.messageBox("Invalid input. Aborting.")
                    return

                filename_base = os.path.splitext(os.path.basename(chosen_path))[0]
                success = new_doc.saveAs(filename_base, selected_folder, '', '')
                if not success:
                    ui.messageBox("Failed to save new design to cloud.")
                    return

        
                savedFile = None
                for _ in range(30):  # 30 × 0.5s = 15 seconds
                    for i in range(selected_folder.dataFiles.count):
                        file = selected_folder.dataFiles.item(i)
                        if file.name == filename_base:
                            savedFile = file
                            break
                    if savedFile:
                        break
                    adsk.doEvents()
                    adsk.core.Application.get().userInterface.palettes.itemById('TextCommands').writeText(
                        f"Waiting for cloud file '{filename_base}' to appear..."
                    )
                    adsk.core.Application.get().activeViewport.refresh()
                    adsk.core.Application.get().wait(0.5)

                if not savedFile:
                    ui.messageBox("Saved document could not be found after waiting. Try again.")
                    return

                new_doc.close(False)
                current_doc.activate()

                originalDesign = None
                for i in range(current_doc.products.count):
                    prod = current_doc.products.item(i)
                    if prod.objectType == adsk.fusion.Design.classType():
                        originalDesign = adsk.fusion.Design.cast(prod)
                        break

                if not originalDesign:
                    ui.messageBox("The active document is not a Fusion design.")
                    return

                rootComp = originalDesign.rootComponent
                if not rootComp:
                    ui.messageBox("The original design has no valid root component.")
                    return

                transform = adsk.core.Matrix3D.create()

                try:
                    rootComp.occurrences.addByInsert(savedFile, transform, True)
                except RuntimeError as e:
                    if "group" in str(e).lower():
                        ui.messageBox("⚠️ Cannot insert into this document. It has been saved to chosen folder, but not inserted. Please insert manually.")
                    else:
                        raise
                else:
                    ui.messageBox(f"✅ Saved as '{filename_base}.f3d'")




                


            else:
                design = adsk.fusion.Design.cast(app.activeProduct)
                if not design:
                    ui.messageBox("No active Fusion design open. Please open or create a design first.")
                    return
                import_mgr = app.importManager
                step_options = import_mgr.createSTEPImportOptions(chosen_path)
                import_mgr.importToTarget(step_options, design.rootComponent)
                ui.messageBox(f'Successfully imported: {os.path.basename(chosen_path)}')

        except Exception:
            if ui:
                ui.messageBox(f'Failed:\n{traceback.format_exc()}')
