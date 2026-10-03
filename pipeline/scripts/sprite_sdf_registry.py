"""V9 auxiliary planes: bounded SDF and nearest native Q3m material offsets."""
import numpy as np

PAD = 6
EMPTY = 0xffffffff

def planes(indices, field):
    from scipy import ndimage
    foreground = np.pad(indices >= 2, PAD)
    if field.shape != foreground.shape or not np.isfinite(field).all():
        raise ValueError('SDF extent or nonfinite distance')
    q = np.clip(np.rint(field * 16), -64, 63).astype(np.int16)
    q[(q == 0) & (field > 0)] = 1
    q[(q == 0) & (field < 0)] = -1
    sdf = (q + 64).astype(np.uint8)
    if foreground.any():
        nearest = ndimage.distance_transform_edt(~foreground, return_distances=False, return_indices=True)
        material = ((nearest[0] - PAD) * indices.shape[1] + nearest[1] - PAD).astype('<u4')
        if not np.all(indices.ravel()[material] >= 2):
            raise ValueError('nearest material references background')
    else:
        material = np.full(foreground.shape, EMPTY, dtype='<u4')
    return sdf, material

def validate(indices, sdf, material):
    shape = (indices.shape[0] + 2 * PAD, indices.shape[1] + 2 * PAD)
    if sdf.dtype != np.uint8 or sdf.shape != shape or np.any(sdf >= 128):
        raise ValueError('invalid V9 SDF')
    if material.dtype != np.dtype('<u4') or material.shape != shape:
        raise ValueError('invalid V9 material map')
    if np.any(indices >= 2):
        if np.any(material >= indices.size) or np.any(indices.ravel()[material] < 2):
            raise ValueError('invalid V9 foreground reference')
    elif np.any(material != EMPTY) or np.any(sdf >= 64):
        raise ValueError('invalid empty V9 foreground')
