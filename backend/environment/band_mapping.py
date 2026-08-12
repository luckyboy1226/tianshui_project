import re


_ROLE_ORDER = ('blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'thermal')

_ROLE_ALIASES = {
    'blue': {'BLUE'},
    'green': {'GREEN'},
    'red': {'RED'},
    'nir': {'NIR', 'NEAR_INFRARED', 'NEARIR', 'NEAR_IR'},
    'swir1': {'SWIR1', 'SWIR_1', 'MIR1', 'MIR_1'},
    'swir2': {'SWIR2', 'SWIR_2', 'MIR2', 'MIR_2'},
    'thermal': {'THERMAL', 'LST', 'TIR', 'TIRS', 'TIRS1', 'ST_B10', 'ST_B6'},
}

_TASSELED_CAP_FAMILIES = {
    'landsat_oli_like': {
        'brightness': [0.3029, 0.2786, 0.4733, 0.5599, 0.5080, 0.1872],
        'greenness': [-0.2941, -0.2430, -0.5424, 0.7276, 0.0713, -0.1608],
        'wetness': [0.1511, 0.1973, 0.3283, 0.3407, -0.7117, -0.4559],
        'fourth': [-0.8239, 0.0849, 0.4396, -0.0580, 0.2013, -0.2773],
        'fifth': [-0.3294, 0.0557, 0.1056, 0.1855, -0.4349, 0.8085],
        'sixth': [0.1079, -0.9023, 0.4119, 0.0575, -0.0259, 0.0252],
    },
    'landsat_tm_like': {
        'brightness': [0.3037, 0.2793, 0.4743, 0.5585, 0.5082, 0.1863],
        'greenness': [-0.2848, -0.2435, -0.5436, 0.7243, 0.0840, -0.1800],
        'wetness': [0.1509, 0.1973, 0.3279, 0.3406, -0.7112, -0.4572],
    },
}

_PROFILE_SETTINGS = {
    'unknown': {
        'tasseled_cap_family': None,
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'landsat_c2_l2_sr': {
        'tasseled_cap_family': 'landsat_oli_like',
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'landsat_c2_l2_st': {
        'tasseled_cap_family': 'landsat_oli_like',
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': 0.00341802,
        'thermal_offset_fallback': 149.0,
        'thermal_units': 'kelvin',
    },
    'landsat_tm_c2_l2_sr': {
        'tasseled_cap_family': 'landsat_tm_like',
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'landsat_tm_c2_l2_st': {
        'tasseled_cap_family': 'landsat_tm_like',
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': 0.00341802,
        'thermal_offset_fallback': 149.0,
        'thermal_units': 'kelvin',
    },
    'landsat_oli_tirs': {
        'tasseled_cap_family': 'landsat_oli_like',
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'landsat_tm_etm': {
        'tasseled_cap_family': 'landsat_tm_like',
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'sentinel_2_msi': {
        'tasseled_cap_family': None,
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'reflective_6band': {
        'tasseled_cap_family': 'landsat_oli_like',
        'approximate_tasseled_cap': True,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'reflective_5band': {
        'tasseled_cap_family': None,
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'generic_4band': {
        'tasseled_cap_family': None,
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'rgb': {
        'tasseled_cap_family': None,
        'approximate_tasseled_cap': False,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
    'described_multispectral': {
        'tasseled_cap_family': 'landsat_oli_like',
        'approximate_tasseled_cap': True,
        'thermal_scale_fallback': None,
        'thermal_offset_fallback': None,
        'thermal_units': None,
    },
}


def _empty_mapping(profile='unknown'):
    mapping = {role: None for role in _ROLE_ORDER}
    mapping['profile'] = profile
    return mapping


def _normalized_label(value):
    if not value:
        return ''
    normalized = re.sub(r'[^A-Z0-9]+', '_', str(value).strip().upper()).strip('_')
    return normalized


def _normalized_labels(values):
    return [_normalized_label(value) for value in (values or [])]


def get_profile_settings(profile):
    return _PROFILE_SETTINGS.get(profile or 'unknown', _PROFILE_SETTINGS['unknown'])


def get_band_descriptions(dataset, band_count=None):
    """Read band descriptions from rasterio or GDAL datasets."""
    if dataset is None:
        return []

    descriptions = getattr(dataset, 'descriptions', None)
    if descriptions:
        return list(descriptions)

    if band_count is None:
        band_count = int(
            getattr(dataset, 'count', 0) or
            getattr(dataset, 'RasterCount', 0) or
            0
        )

    get_raster_band = getattr(dataset, 'GetRasterBand', None)
    if not callable(get_raster_band):
        return []

    results = []
    for index in range(1, band_count + 1):
        try:
            results.append(get_raster_band(index).GetDescription() or '')
        except Exception:
            results.append('')
    return results


def get_band_scales(dataset, band_count=None):
    if dataset is None:
        return []

    scales = getattr(dataset, 'scales', None)
    if scales:
        return list(scales)

    if band_count is None:
        band_count = int(
            getattr(dataset, 'count', 0) or
            getattr(dataset, 'RasterCount', 0) or
            0
        )

    get_raster_band = getattr(dataset, 'GetRasterBand', None)
    if not callable(get_raster_band):
        return []

    values = []
    for index in range(1, band_count + 1):
        try:
            values.append(get_raster_band(index).GetScale())
        except Exception:
            values.append(None)
    return values


def get_band_offsets(dataset, band_count=None):
    if dataset is None:
        return []

    offsets = getattr(dataset, 'offsets', None)
    if offsets:
        return list(offsets)

    if band_count is None:
        band_count = int(
            getattr(dataset, 'count', 0) or
            getattr(dataset, 'RasterCount', 0) or
            0
        )

    get_raster_band = getattr(dataset, 'GetRasterBand', None)
    if not callable(get_raster_band):
        return []

    values = []
    for index in range(1, band_count + 1):
        try:
            values.append(get_raster_band(index).GetOffset())
        except Exception:
            values.append(None)
    return values


def get_band_units(dataset, band_count=None):
    if dataset is None:
        return []

    units = getattr(dataset, 'units', None)
    if units:
        return list(units)

    if band_count is None:
        band_count = int(
            getattr(dataset, 'count', 0) or
            getattr(dataset, 'RasterCount', 0) or
            0
        )

    get_raster_band = getattr(dataset, 'GetRasterBand', None)
    if not callable(get_raster_band):
        return []

    values = []
    for index in range(1, band_count + 1):
        try:
            values.append(get_raster_band(index).GetUnitType())
        except Exception:
            values.append(None)
    return values


def get_band_scale_offset(dataset, band_index, band_count=None):
    scales = get_band_scales(dataset, band_count=band_count)
    offsets = get_band_offsets(dataset, band_count=band_count)
    scale = scales[band_index] if band_index < len(scales) else None
    offset = offsets[band_index] if band_index < len(offsets) else None

    if scale in (None, 0):
        scale = 1.0
    if offset is None:
        offset = 0.0
    return float(scale), float(offset)


def get_band_unit(dataset, band_index, band_count=None):
    units = get_band_units(dataset, band_count=band_count)
    if band_index < len(units):
        return units[band_index]
    return None


def normalized_description_mapping(descriptions):
    mapping = {}
    for index, description in enumerate(descriptions or []):
        normalized = _normalized_label(description)
        if normalized:
            mapping[normalized] = index
    return mapping


def _extract_numeric_band_ids(description_mapping):
    numeric_mapping = {}
    for label, index in description_mapping.items():
        match = re.search(r'(?:^|_)(?:SR_B|ST_B|BAND_|B)(\d{1,2})(?:$|_)', label)
        if match:
            numeric_mapping[int(match.group(1))] = index
    return numeric_mapping


def _has_labels(description_mapping, *labels):
    return all(label in description_mapping for label in labels)


def _mapping_from_numeric_descriptions(description_mapping, band_count):
    numeric_mapping = _extract_numeric_band_ids(description_mapping)

    if {2, 3, 4, 5, 6, 7}.issubset(numeric_mapping) and any(
        label.startswith('SR_B') for label in description_mapping
    ):
        mapping = _empty_mapping('landsat_c2_l2_st' if 10 in numeric_mapping else 'landsat_c2_l2_sr')
        mapping.update({
            'blue': numeric_mapping[2],
            'green': numeric_mapping[3],
            'red': numeric_mapping[4],
            'nir': numeric_mapping[5],
            'swir1': numeric_mapping[6],
            'swir2': numeric_mapping[7],
            'thermal': numeric_mapping.get(10),
        })
        return mapping, 'high'

    if {1, 2, 3, 4, 5, 7}.issubset(numeric_mapping) and any(
        label.startswith('SR_B') for label in description_mapping
    ):
        has_surface_temperature = 6 in numeric_mapping and any(label.startswith('ST_B6') for label in description_mapping)
        mapping = _empty_mapping('landsat_tm_c2_l2_st' if has_surface_temperature else 'landsat_tm_c2_l2_sr')
        mapping.update({
            'blue': numeric_mapping[1],
            'green': numeric_mapping[2],
            'red': numeric_mapping[3],
            'nir': numeric_mapping[4],
            'swir1': numeric_mapping[5],
            'thermal': numeric_mapping.get(6),
            'swir2': numeric_mapping[7],
        })
        return mapping, 'high'

    if {2, 3, 4, 8, 11, 12}.issubset(numeric_mapping):
        mapping = _empty_mapping('sentinel_2_msi')
        mapping.update({
            'blue': numeric_mapping[2],
            'green': numeric_mapping[3],
            'red': numeric_mapping[4],
            'nir': numeric_mapping[8],
            'swir1': numeric_mapping[11],
            'swir2': numeric_mapping[12],
        })
        return mapping, 'high'

    if band_count >= 10 and {2, 3, 4, 5, 6, 7}.issubset(numeric_mapping):
        mapping = _empty_mapping('landsat_oli_tirs')
        mapping.update({
            'blue': numeric_mapping[2],
            'green': numeric_mapping[3],
            'red': numeric_mapping[4],
            'nir': numeric_mapping[5],
            'swir1': numeric_mapping[6],
            'swir2': numeric_mapping[7],
            'thermal': numeric_mapping.get(10) if 10 in numeric_mapping else numeric_mapping.get(11),
        })
        return mapping, 'high'

    if band_count in (7, 8) and {1, 2, 3, 4, 5, 7}.issubset(numeric_mapping):
        mapping = _empty_mapping('landsat_tm_etm')
        mapping.update({
            'blue': numeric_mapping[1],
            'green': numeric_mapping[2],
            'red': numeric_mapping[3],
            'nir': numeric_mapping[4],
            'swir1': numeric_mapping[5],
            'thermal': numeric_mapping.get(6),
            'swir2': numeric_mapping[7],
        })
        return mapping, 'high'

    return None, None


def _mapping_from_band_count(band_count):
    if band_count >= 10:
        mapping = _empty_mapping('landsat_oli_tirs')
        mapping.update({
            'blue': 1,
            'green': 2,
            'red': 3,
            'nir': 4,
            'swir1': 5,
            'swir2': 6,
            'thermal': 9,
        })
        return mapping, 'low'

    if band_count in (7, 8):
        mapping = _empty_mapping('landsat_tm_etm')
        mapping.update({
            'blue': 0,
            'green': 1,
            'red': 2,
            'nir': 3,
            'swir1': 4,
            'thermal': 5,
            'swir2': 6,
        })
        return mapping, 'low'

    if band_count == 6:
        mapping = _empty_mapping('reflective_6band')
        mapping.update({
            'blue': 0,
            'green': 1,
            'red': 2,
            'nir': 3,
            'swir1': 4,
            'swir2': 5,
        })
        return mapping, 'low'

    if band_count == 5:
        mapping = _empty_mapping('reflective_5band')
        mapping.update({
            'blue': 0,
            'green': 1,
            'red': 2,
            'nir': 3,
            'swir1': 4,
        })
        return mapping, 'low'

    if band_count == 4:
        mapping = _empty_mapping('generic_4band')
        mapping.update({
            'blue': 0,
            'green': 1,
            'red': 2,
            'nir': 3,
        })
        return mapping, 'low'

    if band_count == 3:
        mapping = _empty_mapping('rgb')
        mapping.update({
            'blue': 2,
            'green': 1,
            'red': 0,
        })
        return mapping, 'low'

    return _empty_mapping(), 'low'


def _explicit_role_mapping(description_mapping):
    mapping = _empty_mapping('described_multispectral')
    found = False
    for role, aliases in _ROLE_ALIASES.items():
        for alias in aliases:
            if alias in description_mapping:
                mapping[role] = description_mapping[alias]
                found = True
                break
    return mapping if found else None


def infer_standard_band_mapping(dataset=None, band_count=None, descriptions=None):
    """
    Infer a semantic band mapping for common multispectral products.

    The result always uses 0-based band indices and may leave unsupported
    semantic roles as None.
    """
    if band_count is None:
        band_count = int(
            getattr(dataset, 'count', 0) or
            getattr(dataset, 'RasterCount', 0) or
            0
        )

    descriptions = descriptions if descriptions is not None else get_band_descriptions(dataset, band_count=band_count)
    description_mapping = normalized_description_mapping(descriptions)
    explicit_mapping = _explicit_role_mapping(description_mapping)
    numeric_mapping, numeric_confidence = _mapping_from_numeric_descriptions(description_mapping, band_count)
    count_mapping, count_confidence = _mapping_from_band_count(band_count)

    if numeric_mapping is not None:
        base_mapping = numeric_mapping
        base_confidence = numeric_confidence
    else:
        base_mapping = count_mapping
        base_confidence = count_confidence

    if explicit_mapping is not None:
        if base_confidence == 'low':
            explicit_index_roles = {
                explicit_mapping[role]: role
                for role in _ROLE_ORDER
                if explicit_mapping.get(role) is not None
            }
            for role in _ROLE_ORDER:
                inferred_index = base_mapping.get(role)
                owner = explicit_index_roles.get(inferred_index)
                if inferred_index is not None and owner and owner != role:
                    base_mapping[role] = None
            base_mapping['profile'] = explicit_mapping['profile']

        for role in _ROLE_ORDER:
            if explicit_mapping.get(role) is not None:
                base_mapping[role] = explicit_mapping[role]
        if base_mapping.get('profile') == 'unknown':
            base_mapping['profile'] = explicit_mapping['profile']

    return base_mapping


def get_tasseled_cap_coefficients(profile):
    settings = get_profile_settings(profile)
    family_name = settings.get('tasseled_cap_family')
    if not family_name:
        return None
    family = _TASSELED_CAP_FAMILIES.get(family_name)
    if not family:
        return None
    return {key: list(value) for key, value in family.items()}


def uses_approximate_tasseled_cap(profile):
    return bool(get_profile_settings(profile).get('approximate_tasseled_cap'))


def has_tasseled_cap_support(mapping):
    if not mapping:
        return False
    coefficients = get_tasseled_cap_coefficients(mapping.get('profile'))
    if not coefficients:
        return False
    return all(mapping.get(role) is not None for role in ('blue', 'green', 'red', 'nir', 'swir1', 'swir2'))


def has_role(mapping, *roles):
    if not mapping:
        return False
    return all(mapping.get(role) is not None for role in roles)


def infer_rgb_bands(dataset=None, mapping=None):
    if dataset is not None:
        colorinterp = [str(item).lower() for item in getattr(dataset, 'colorinterp', ()) or ()]
        if colorinterp:
            rgb_mapping = {}
            for index, name in enumerate(colorinterp, start=1):
                if 'red' in name:
                    rgb_mapping['red_band'] = index
                elif 'green' in name:
                    rgb_mapping['green_band'] = index
                elif 'blue' in name:
                    rgb_mapping['blue_band'] = index
            if len(rgb_mapping) == 3:
                return rgb_mapping

    mapping = mapping or infer_standard_band_mapping(dataset=dataset)
    if has_role(mapping, 'red', 'green', 'blue'):
        return {
            'red_band': mapping['red'] + 1,
            'green_band': mapping['green'] + 1,
            'blue_band': mapping['blue'] + 1,
        }
    return None


def _looks_like_temperature_unit(unit_value):
    normalized = _normalized_label(unit_value)
    if not normalized:
        return False
    return any(token in normalized for token in ('KELVIN', 'CELSIUS', 'DEGC', 'DEG_C', 'TEMPERATURE', 'LST'))


def thermal_band_is_calibrated(mapping=None, dataset=None):
    if not mapping or mapping.get('thermal') is None:
        return False

    profile = mapping.get('profile')
    settings = get_profile_settings(profile)
    if settings.get('thermal_scale_fallback') is not None:
        return True

    if dataset is None:
        return False

    thermal_index = mapping['thermal']
    scale, offset = get_band_scale_offset(dataset, thermal_index)
    if abs(scale - 1.0) > 1e-12 or abs(offset) > 1e-12:
        return True

    if _looks_like_temperature_unit(get_band_unit(dataset, thermal_index)):
        return True

    descriptions = _normalized_labels(get_band_descriptions(dataset))
    if thermal_index < len(descriptions):
        desc = descriptions[thermal_index]
        if any(token in desc for token in ('LST', 'KELVIN', 'CELSIUS', 'TEMPERATURE')):
            return True
    return False


def thermal_conversion_parameters(profile):
    settings = get_profile_settings(profile)
    return settings.get('thermal_scale_fallback'), settings.get('thermal_offset_fallback')


def supported_remote_indices(mapping=None, band_count=None, dataset=None):
    if mapping is None and band_count is None:
        return sorted(['ndvi', 'ndwi', 'ndbi', 'dryness', 'wetness', 'heat', 'greenness', 'rsei'])

    band_count = int(band_count or 0)
    if band_count == 1:
        return ['uploaded_raster']

    mapping = mapping or _empty_mapping()
    rgb_approximation = band_count == 3

    indices = []
    if has_role(mapping, 'nir', 'red') or rgb_approximation:
        indices.append('ndvi')
        indices.append('greenness')
    if has_role(mapping, 'green', 'nir') or rgb_approximation:
        indices.append('ndwi')
    if has_role(mapping, 'swir1', 'nir') or rgb_approximation:
        indices.append('ndbi')
    if has_role(mapping, 'blue', 'green', 'red', 'nir', 'swir1'):
        indices.append('dryness')
    if has_tasseled_cap_support(mapping):
        indices.append('wetness')
    if thermal_band_is_calibrated(mapping=mapping, dataset=dataset):
        indices.append('heat')
    if {'greenness', 'dryness', 'wetness', 'heat'}.issubset(indices):
        indices.append('rsei')

    return sorted(set(indices))
