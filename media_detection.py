import subprocess

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
    method = "ddrescue"
    ddrescue_options = ['--force']
    ddrescue_options.append("-n")
    ddrescue_options.append("-r3")
    ddrescue_options.append("-b 2048")
    ddrescue_options.append("-d")
    
    mapfile = f"{output_path}.map"
    return f"sudo ddrescue {' '.join(ddrescue_options)} {dvd_device} {output_path} {mapfile}"

def prepare_audio_cd_command(dvd_device, output_path):
    if shutil.which("cdparanoia") is None:
        raise RuntimeError("cdparanoia is not installed")
    return f"cdparanoia -B -d {dvd_device} -D 0 -Z {output_path}/track"

def prepare_video_music_dvd_command(dvd_device, output_path):
    if shutil.which("dvdbackup") is None:
        raise RuntimeError("dvdbackup is not installed")
    return f"dvdbackup -i {dvd_device} -o {output_path} -M"
