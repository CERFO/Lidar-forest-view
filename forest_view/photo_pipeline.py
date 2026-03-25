import math
import os
import shutil
import subprocess
from collections import defaultdict

from PIL import Image

from forest_view.logger import get_logger

logger = get_logger(__name__)


def _resolve_hugin_tools(hugin_root=None):
    """Résout les exécutables Hugin depuis PATH puis via un dossier d'installation."""
    tools = (
        'pto_gen',
        'pto_merge',
        'pto_lensstack',
        'pto_var',
        'cpfind',
        'autooptimiser',
        'nona',
    )
    resolved = {}
    fallback_root = hugin_root or r'C:\Program Files\Hugin'
    for tool in tools:
        path = shutil.which(tool) or shutil.which(f'{tool}.exe')
        if path:
            resolved[tool] = path
            continue
        candidate = os.path.join(fallback_root, 'bin', f'{tool}.exe')
        if os.path.exists(candidate):
            resolved[tool] = candidate
            continue
        raise RuntimeError(
            f"Exécutable Hugin introuvable: {tool}. "
            "Ajoutez Hugin au PATH ou configurez hugin_root."
        )
    return resolved


def get_valid_pairs(directory):
    """
    Parcourt les photos d'un répertoire et identifie les paires d'images lisibles.

    Paramètres:
        directory (str): Chemin du répertoire contenant les photos

    Retourne:
        liste [image avant, image arrière, timestamp image avant relatif à la première image]
    """
    photo_pairs = defaultdict(dict)
    first_photo_stamp = None

    for photo in os.listdir(directory):
        name, _ = os.path.splitext(photo)
        try:
            id, side, timestamp = name.split('_')
        except Exception:
            continue
        if first_photo_stamp is None:
            first_photo_stamp = int(timestamp)
        photo_pairs[id][side] = (photo, int(timestamp) - first_photo_stamp)

    valid_pairs = []
    for pair in photo_pairs.values():
        try:
            # verify() closes the file handle, so open fresh copies just for the check
            Image.open(os.path.join(directory, pair['F'][0])).verify()
            Image.open(os.path.join(directory, pair['R'][0])).verify()
        except Exception:
            continue
        if len(pair) == 2 and 'F' in pair and 'R' in pair:
            valid_pairs.append([
                [os.path.join(directory, pair['F'][0]), os.path.join(directory, pair['R'][0])],
                pair['F'][1]
            ])
    print(f'{len(valid_pairs)} paires valides trouvées')
    logger.info('%s paires valides trouvées', len(valid_pairs))
    return valid_pairs


def stitch_photos(pair_list, outdirectory, calibration=None, hugin_root=None, index_start=0):
    """
    Assemble des paires de photos fisheye en photos panoramiques.

    Paramètres:
        pair_list (list): Liste de paires d'images à assembler
        outdirectory (str): Répertoire de sortie pour les images assemblées
        calibration (dict, optional): Fichier de calibration
        hugin_root (str): Chemin vers le répertoire d'installation de Hugin (optionnel)
        index_start (int): Index de départ pour le numérotage des panoramas

    Retourne:
        pair_list modifié (chemins des panoramas)
    """
    os.makedirs(os.path.join(outdirectory, 'panoramas'), exist_ok=True)
    hugin_tools = _resolve_hugin_tools(hugin_root)

    if calibration is None:
        calibration_values = {
            'yF': 0, 'rF': -90, 'pF': 0, 'vF': 200,
            'aF': 0, 'bF': 0, 'cF': 0, 'dF': 0, 'eF': 0,
            'yR': 180, 'rR': -90, 'pR': 0, 'vR': 200,
            'aR': 0, 'bR': 0, 'cR': 0, 'dR': 0, 'eR': 0
        }
        crop_values = {
            'lF': 50, 'rF': 1870, 'tF': 50, 'bF': 1870,
            'lR': 50, 'rR': 1870, 'tR': 50, 'bR': 1870
        }
    else:
        forward_lens_params = calibration.get('lensParameters', {}).get('forwardLensCalibration', {})
        rearward_lens_params = calibration.get('lensParameters', {}).get('rearwardLensCalibration', {})
        calibration_values = {
            'yF': forward_lens_params.get('yaw'), 'rF': forward_lens_params.get('roll'),
            'pF': forward_lens_params.get('pitch'),
            'vF': 200 if forward_lens_params.get('fov') == 0 else forward_lens_params.get('fov'),
            'aF': forward_lens_params.get('coeffA'), 'bF': forward_lens_params.get('coeffB'),
            'cF': forward_lens_params.get('coeffC'),
            'dF': forward_lens_params.get('horizontalOffset'), 'eF': forward_lens_params.get('verticalOffset'),
            'yR': rearward_lens_params.get('yaw'), 'rR': rearward_lens_params.get('roll'),
            'pR': rearward_lens_params.get('pitch'),
            'vR': 200 if rearward_lens_params.get('fov') == 0 else rearward_lens_params.get('fov'),
            'aR': rearward_lens_params.get('coeffA'), 'bR': rearward_lens_params.get('coeffB'),
            'cR': rearward_lens_params.get('coeffC'),
            'dR': rearward_lens_params.get('horizontalOffset'), 'eR': rearward_lens_params.get('verticalOffset')
        }
        forward_lens_crop = calibration.get('lensParameters', {}).get('forwardLensSelectionArea', {})
        rearward_lens_crop = calibration.get('lensParameters', {}).get('rearwardLensSelectionArea', {})
        crop_values = {
            'lF': forward_lens_crop.get('Left'), 'rF': forward_lens_crop.get('Right'),
            'tF': forward_lens_crop.get('Top'), 'bF': forward_lens_crop.get('Bottom'),
            'lR': rearward_lens_crop.get('Left'), 'rR': rearward_lens_crop.get('Right'),
            'tR': rearward_lens_crop.get('Top'), 'bR': rearward_lens_crop.get('Bottom')
        }
        if all(value == 0 for value in crop_values.values()):
            crop_values = {
                'lF': 50, 'rF': 1870, 'tF': 50, 'bF': 1870,
                'lR': 50, 'rR': 1870, 'tR': 50, 'bR': 1870
            }

    _temp_files = ('projet1.pto', 'projet2.pto', 'projet_merge.pto')

    def _run(cmd):
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            tool = os.path.basename(cmd[0])
            stderr = result.stderr.decode(errors='replace').strip()
            logger.error('%s a échoué (code %d): %s', tool, result.returncode, stderr)
            raise RuntimeError(f'{tool} a échoué (code {result.returncode}): {stderr}')

    for i, pair in enumerate(pair_list):
        imgF_path = pair[0][0]
        imgR_path = pair[0][1]
        try:
            _run([
                hugin_tools['pto_gen'],
                '-o', 'projet1.pto', '-p', '2',
                '-c', f'{crop_values["lF"]},{crop_values["rF"]},{crop_values["tF"]},{crop_values["bF"]}',
                imgF_path
            ])
            _run([
                hugin_tools['pto_gen'],
                '-o', 'projet2.pto', '-p', '2',
                '-c', f'{crop_values["lR"]},{crop_values["rR"]},{crop_values["tR"]},{crop_values["bR"]}',
                imgR_path
            ])
            _run([
                hugin_tools['pto_merge'],
                '-o', 'projet_merge.pto', 'projet1.pto', 'projet2.pto'
            ])
            _run([
                hugin_tools['pto_lensstack'],
                '-o', 'projet_merge.pto', '--new-lens', 'i1', 'projet_merge.pto'
            ])
            _run([
                hugin_tools['pto_var'], '-o', 'projet_merge.pto',
                '--set', f'y0={calibration_values["yF"]}, r0={calibration_values["rF"]}, p0={calibration_values["pF"]}',
                '--set', f'v0={calibration_values["vF"]}',
                '--set', f'a0={calibration_values["aF"]}, b0={calibration_values["bF"]}, c0={calibration_values["cF"]}',
                '--set', f'd0={calibration_values["dF"]}, e0={calibration_values["eF"]}',
                '--set', f'y1={calibration_values["yR"]}, r1={calibration_values["rR"]}, p1={calibration_values["pR"]}',
                '--set', f'v1={calibration_values["vR"]}',
                '--set', f'a1={calibration_values["aR"]}, b1={calibration_values["bR"]}, c1={calibration_values["cR"]}',
                '--set', f'd1={calibration_values["dR"]}, e1={calibration_values["eR"]}',
                '--opt', 'v0,v1,y1,p1,r1', 'projet_merge.pto'
            ])
            _run([
                hugin_tools['cpfind'],
                '-o', 'projet_merge.pto', '--fullscale', 'projet_merge.pto'
            ])
            _run([
                hugin_tools['autooptimiser'],
                '-o', 'projet_merge.pto', '-n', 'projet_merge.pto'
            ])
            _run([
                hugin_tools['nona'],
                '-o', os.path.join(outdirectory, 'panoramas', f'pano{i + index_start:04d}'),
                '-m', 'JPEG', 'projet_merge.pto'
            ])
            pair_list[i][0] = f'pano{i + index_start:04d}.jpg'
        except RuntimeError:
            logger.warning('Paire %d ignorée en raison d\'une erreur Hugin', i)
        finally:
            for f in _temp_files:
                if os.path.exists(f):
                    os.remove(f)

    print('Les photos sont assemblées!')
    logger.info('Les photos sont assemblées!')
    return pair_list


def get_photo_locations(photo_list, trajectory, trajectory_header, calibration):
    """
    Associe les photos à leurs emplacements dans le trajet.

    Paramètres:
        photo_list (list): Liste des photos à associer
        trajectory (list): Liste des points de la trajectoire
        trajectory_header (list): En-tête du fichier trajectoire
        calibration (dict): Dictionnaire des paramètres de calibration

    Retourne:
        photo_list avec x, y, z, roll, pitch, yaw ajoutés
    """
    first_traj_stamp = float(trajectory[0][0])
    iteration = 0
    time_col = trajectory_header.index('//world_time') if '//world_time' in trajectory_header else trajectory_header.index('%time')
    for entry in trajectory:
        stamp = float(entry[time_col])
        if stamp > (photo_list[iteration][1]) / 1000 + first_traj_stamp - 4:
            roll, yaw, pitch = quaternion_to_euler(
                float(entry[trajectory_header.index('q0')]),
                float(entry[trajectory_header.index('q1')]),
                float(entry[trajectory_header.index('q2')]),
                float(entry[trajectory_header.index('q3')])
            )
            photo_list[iteration][1] = stamp
            photo_list[iteration].extend([
                entry[trajectory_header.index('x')],
                entry[trajectory_header.index('y')],
                entry[trajectory_header.index('z')],
                roll, pitch, yaw + 180
            ])
            iteration += 1
        if iteration >= len(photo_list):
            break
    print('Photos localisées!')
    logger.info('Photos localisées!')
    return photo_list


def quaternion_to_euler(qw, qx, qy, qz):
    """
    Convertit un quaternion en angles d'Euler (roulis, tangage, lacet) en degrés.

    Paramètres:
        qw, qx, qy, qz: Composantes du quaternion (w, x, y, z)

    Retourne:
        tuple: (roll, pitch, yaw) en degrés
    """
    norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if norm == 0:
        return (0.0, 0.0, 0.0)
    qw, qx, qy, qz = qw / norm, qx / norm, qy / norm, qz / norm
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2 * (qw * qy - qz * qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return (math.degrees(roll), math.degrees(pitch), math.degrees(yaw))
