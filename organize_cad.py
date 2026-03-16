import os
import shutil
from typing import List

DOWNLOAD_DIR = "CAD_Files"

KEYWORD_CATEGORIES = {
    "motor controller": ["ELECTRONICS", "Controllers"], "servo controller": ["ELECTRONICS", "Controllers"], "spark": ["ELECTRONICS", "Controllers"],
    "sensor": ["ELECTRONICS", "Sensors"], "cable": ["ELECTRONICS", "Cables"], "wire": ["ELECTRONICS", "Cables"], "battery": ["ELECTRONICS", "Power"],
    "power": ["ELECTRONICS", "Power"], "switch": ["ELECTRONICS", "Power"], "control hub": ["ELECTRONICS", "Control Systems"],
    "expansion hub": ["ELECTRONICS", "Control Systems"], "camera": ["ELECTRONICS", "Vision"], "vision": ["ELECTRONICS", "Vision"], "logic level": ["ELECTRONICS", "Sensors"],
    "encoder": ["ELECTRONICS", "Sensors"], "board": ["ELECTRONICS", "Boards"], "limelight": ["ELECTRONICS", "Vision"], "roborio": ["ELECTRONICS", "Control Systems"],
    "memory card": ["ELECTRONICS", "Storage"], "regulator": ["ELECTRONICS", "Power"], "bec": ["ELECTRONICS", "Power"], "led light": ["ELECTRONICS", "Lighting"],
    "lidar": ["ELECTRONICS", "Sensors"], "signal light": ["ELECTRONICS", "Lighting"], "slip ring": ["ELECTRONICS", "Misc"], "meter": ["ELECTRONICS", "Misc"],
    "motor": ["MOTION", "Motors"], "servo": ["MOTION", "Servos"], "wheel": ["MOTION", "Wheels"], "gear": ["MOTION", "Gears"], "sprocket": ["MOTION", "Sprockets"],
    "pulley": ["MOTION", "Pulleys"], "belt": ["MOTION", "Belts"], "chain": ["MOTION", "Chain"], "bearing": ["MOTION", "Bearings"], "shaft": ["MOTION", "Shafting"],
    "axle": ["MOTION", "Shafting"], "hub": ["MOTION", "Hubs"], "mecanum": ["MOTION", "Wheels"], "omni": ["MOTION", "Wheels"], "caster": ["MOTION", "Wheels"],
    "pinion": ["MOTION", "Gears"], "gearbox": ["MOTION", "Gearboxes"], "linear": ["MOTION", "Linear Motion"], "lead screw": ["MOTION", "Linear Motion"],
    "tire": ["MOTION", "Wheels"], "coupler": ["MOTION", "Couplers"], "worm": ["MOTION", "Gears"], "slider": ["MOTION", "Linear Motion"], "pillow block": ["MOTION", "Bearings"],
    "drive": ["MOTION", "Chassis"], "turntable": ["MOTION", "Turntables"], "spool": ["MOTION", "Spools"], "tensioner": ["MOTION", "Chain"], "track": ["MOTION", "Tracks"],
    "robits": ["MOTION", "Kits"], "strafer": ["MOTION", "Chassis"],
    "channel": ["STRUCTURE", "Channel"], "extrusion": ["STRUCTURE", "Extrusion"], "tube": ["STRUCTURE", "Tubing"], "plate": ["STRUCTURE", "Plates"],
    "bracket": ["STRUCTURE", "Brackets"], "mount": ["STRUCTURE", "Mounts"], "beam": ["STRUCTURE", "Beams"], "rail": ["STRUCTURE", "Rails"],
    "standoff": ["STRUCTURE", "Standoffs"], "spacer": ["STRUCTURE", "Spacers"], "gusset": ["STRUCTURE", "Gussets"], "spline": ["STRUCTURE", "Splines"],
    "sheet": ["STRUCTURE", "Materials"], "polycarbonate": ["STRUCTURE", "Materials"], "rod": ["STRUCTURE", "Tubing"], "churro": ["STRUCTURE", "Tubing"],
    "disk": ["STRUCTURE", "Plates"], "chassis": ["STRUCTURE", "Chassis"], "box": ["STRUCTURE", "Enclosures"], "enclosure": ["STRUCTURE", "Enclosures"],
    "frame": ["STRUCTURE", "Frames"], "pipe": ["STRUCTURE", "Tubing"], "tray": ["STRUCTURE", "Misc"], "table": ["STRUCTURE", "Misc"],
    "panel": ["STRUCTURE", "Panels"], "perimeter": ["STRUCTURE", "Misc"], "support": ["STRUCTURE", "Brackets"], "container": ["STRUCTURE", "Misc"],
    "brace": ["STRUCTURE", "Brackets"], "upright": ["STRUCTURE", "Brackets"],
    "screw": ["HARDWARE", "Screws"], "nut": ["HARDWARE", "Nuts"], "bolt": ["HARDWARE", "Screws"], "washer": ["HARDWARE", "Washers"],
    "collar": ["HARDWARE", "Collars"], "zip tie": ["HARDWARE", "Misc"], "fastener": ["HARDWARE", "Misc"], "spring": ["HARDWARE", "Springs"],
    "bungee": ["HARDWARE", "Springs"], "surgical tubing": ["HARDWARE", "Tubing"], "insert": ["HARDWARE", "Misc"], "shim": ["HARDWARE", "Spacers"],
    "adapter": ["HARDWARE", "Adapters"], "bushing": ["HARDWARE", "Bearings"], "retaining ring": ["HARDWARE", "Rings"], "tee": ["HARDWARE", "Pipe Fittings"],
    "elbow": ["HARDWARE", "Pipe Fittings"], "valve": ["HARDWARE", "Pneumatics"], "manifold": ["HARDWARE", "Pneumatics"], "air cylinder": ["HARDWARE", "Pneumatics"],
    "compressor": ["HARDWARE", "Pneumatics"], "latch": ["HARDWARE", "Misc"], "block": ["HARDWARE", "Misc"], "nubs": ["HARDWARE", "Misc"],
    "ring": ["HARDWARE", "Rings"], "pneumatic": ["HARDWARE", "Pneumatics"], "solenoid": ["HARDWARE", "Pneumatics"], "strap": ["HARDWARE", "Misc"],
    "cam follower": ["HARDWARE", "Bearings"], "hardware": ["HARDWARE", "Misc"], "hardware kit": ["HARDWARE", "Kits"],
    "kit": ["KITS", "Misc"]
}

def guess_category_from_name(name: str) -> List[str]:
    lower_name = name.lower()
    for kw, cat_list in KEYWORD_CATEGORIES.items():
        if kw in lower_name:
            return cat_list
    return ["UNCATEGORIZED"]

def organize():
    print("====================================")
    print("      CadGrab Folder Organizer      ")
    print("====================================")
    
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Directory {DOWNLOAD_DIR} does not exist. Nothing to organize.")
        return
        
    # We want to pull items out of 'UNCATEGORIZED' *AND* any root-level folders 
    # to drop them into deeper subfolders as defined by the new rules.
    directories_to_scan = [
        "UNCATEGORIZED", 
        "ELECTRONICS", 
        "HARDWARE", 
        "KITS", 
        "MOTION", 
        "STRUCTURE", 
        "HOME HOME"
    ]
    
    files_to_move = []
    
    print("Scanning for top-level or uncategorized files...")
    
    for relative_dir in directories_to_scan:
        source_dir = os.path.join(DOWNLOAD_DIR, relative_dir)
        if os.path.exists(source_dir):
            # Only get files immediately inside this directory, not subfolders
            for f in os.listdir(source_dir):
                source_path = os.path.join(source_dir, f)
                if os.path.isfile(source_path) and (f.lower().endswith('.step') or f.lower().endswith('.stp')):
                    files_to_move.append((source_path, f, relative_dir))
                    
    if not files_to_move:
        print("No CAD files found needing organization.")
        return
        
    print(f"Found {len(files_to_move)} files to organize.\n")
    
    moved_count = 0
    for source_path, filename, origin_dir in files_to_move:
        guessed_breadcrumbs = guess_category_from_name(filename)
        
        # Don't move a file if it resolved to UNCATEGORIZED and is already in UNCATEGORIZED
        if guessed_breadcrumbs == ["UNCATEGORIZED"] and origin_dir == "UNCATEGORIZED":
            continue
            
        target_dir = os.path.join(DOWNLOAD_DIR, *guessed_breadcrumbs)
        target_path = os.path.join(target_dir, filename)
        
        # Make sure we're actually moving it somewhere new
        if source_path == target_path:
            continue
            
        os.makedirs(target_dir, exist_ok=True)
        try:
            # Handle if file already exists in target directory
            if os.path.exists(target_path):
                print(f"[SKIPPED] {filename} already exists perfectly organized.")
                os.remove(source_path) # Safe to delete duplicate
            else:
                shutil.move(source_path, target_path)
                print(f"Moved: {filename} -> {'/'.join(guessed_breadcrumbs)}")
            moved_count += 1
        except Exception as e:
            print(f"Failed to move {filename}: {e}")
                
    print(f"\nOrganization complete! Moved {moved_count} out of {len(files_to_move)} files into proper subcategories.")

if __name__ == "__main__":
    organize()
