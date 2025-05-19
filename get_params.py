def get_params_static_api(apikey=None, ll=None, spn=None, pt=None, bbox=None,
               z=None, size=None, scale=None, pl=None, ):
    res = {}
    if apikey is not None:
        res['apikey'] = apikey
    if bbox is not None:
        res['bbox'] = bbox
    else:
        if ll is not None:
            res['ll'] = ",".join(ll)
        if spn is not None:
            res['spn'] = ",".join(spn)
    if z is not None:
        res['z'] = int(z)
    if size is not None:
        res['size'] = ','.join([str(i) for i in size])
    if scale is not None:
        res['scale'] = float(scale)
    if pl is not None:
        res['pl'] = pl
    if pt is not None:
        res['pt'] = pt
    return res


def get_params_ppo(apikey=None, ll=None, spn=None, text=None, bbox=None,
               type1=None):
    res = {"lang": "ru_RU"}
    if apikey is not None:
        res['apikey'] = apikey
    if bbox is not None:
        res['bbox'] = bbox
    else:
        if ll is not None:
            res['ll'] = ll
        if spn is not None:
            res['spn'] = spn
    if type1 is not None:
        res['type'] = type1
    if text is not None:
        res['text'] = text
    return res
