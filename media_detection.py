import subprocess
import shutil

def detect_media_type(device):
    try:
        result = subprocess.run(['blkid', '-p', '-o', 'value', '-s', 'TYPE', device], 
                                capture_output=True, text=True, check=True)
        media_type = result.stdout.strip()
        
        if media_type == "udf":
            return "Data CD/DVD"
        elif media_type == "iso9660":
            # Check for audio CD regardless of /dev/cdrom existence
            audio_check = subprocess.run(['cdparanoia', '-d', device, '-Q'], 
                                         capture_output=True, text=True)
            if "audio tracks" in audio_check.stderr:
                return "Audio CD"
            return "Data CD/DVD"
        else:
            # Check for Video DVD
            video_check = subprocess.run(['dvdbackup', '--info', '-i', device], 
                                         capture_output=True, text=True)
            if "DVD-Video information" in video_check.stdout:
                return "Video/Music DVD"
            return "Unknown"
    except subprocess.CalledProcessError:
        return "Unknown"
    
def prepare_command(media_type, dvd_device, output_path):
    if media_type == "Data CD/DVD":
        return prepare_data_cd_dvd_command(dvd_device, output_path)
    elif media_type == "Audio CD":
        return prepare_audio_cd_command(dvd_device, output_path)
    elif media_type == "Video/Music DVD":
        return prepare_video_music_dvd_command(dvd_device, output_path)
    else:
        return None

def prepare_data_cd_dvd_command(dvd_device, output_path):
    method = method_var.get()
    if method == "ddrescue":
        if not check_tool_installed("ddrescue"):
            messagebox.showerror("Error", "ddrescue is not installed. Please install it and try again.")
            return None
        
        ddrescue_options = ['--force']
        if n_option_var.get():
            ddrescue_options.append("-n")
        if r3_option_var.get():
            ddrescue_options.append("-r3")
        if b_option_var.get():
            ddrescue_options.append("-b 2048")
        if d_option_var.get():
            ddrescue_options.append("-d")
        if c_option_var.get():
            ddrescue_options.append("-C")
        
        mapfile = f"{output_path}.map"
        return f"sudo ddrescue {' '.join(ddrescue_options)} {dvd_device} {output_path} {mapfile}"
    else:
        return f"sudo dd if={dvd_device} of={output_path} bs=1M status=progress"
