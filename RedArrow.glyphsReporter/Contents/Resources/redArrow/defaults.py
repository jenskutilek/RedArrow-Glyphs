import objc
from AppKit import NSColor, NSDecimalNumber, NSKeyedArchiver

from redArrow.typing import RedArrowOptionsDict

default_checks: list[str] = [
    "RedArrowCheckExtrema",
    "RedArrowCheckInflections",
    "RedArrowCheckFractionalCoords",
    "RedArrowCheckFractionalTransform",
    "RedArrowCheckSmooth",
    "RedArrowCheckEmptySegments",
    "RedArrowCheckCollinear",
    "RedArrowCheckSemiHV",
    # "RedArrowCheckClosepath",
    "RedArrowCheckZeroHandles",
    "RedArrowCheckBboxHandles",
    "RedArrowCheckShortSegments",
    "RedArrowCheckSpikes",
]

default_options: RedArrowOptionsDict = {
    # Checks
    "RedArrowCheckExtrema": True,
    "RedArrowCheckInflections": True,
    "RedArrowCheckFractionalCoords": True,
    "RedArrowCheckFractionalTransform": True,
    "RedArrowCheckSmooth": True,
    "RedArrowCheckEmptySegments": True,
    "RedArrowCheckCollinear": True,
    "RedArrowCheckSemiHV": True,
    "RedArrowCheckClosepath": True,
    "RedArrowCheckZeroHandles": True,
    "RedArrowCheckBboxHandles": True,
    "RedArrowCheckShortSegments": True,
    "RedArrowCheckSpikes": True,
    # Options
    "RedArrowIgnoreWarnings": False,
    "RedArrowExtremaCalculateBadness": False,
    "RedArrowExtremaIgnoreBadnessBelow": 0,
    "RedArrowSmoothMaxDistance": 4,
    "RedArrowCheckSemiHVMinDistance": 30,
    "RedArrowCheckSemiHVMaxDistance": 2,
    "RedArrowCheckFractionalIgnorePointZero": True,
    "RedArrowCollinearMaxDistance": 2,
    "RedArrowGridLengthH": 1,
    "RedArrowGridLengthV": 1,
    "RedArrowZeroHandlesMaxDistance": 0,
    "RedArrowInflectionMin": 0.3,
    "RedArrowSpikeAngle": 0.49,
}

option_types: dict[str, str] = {
    "RedArrowIgnoreWarnings": "bool",
    "RedArrowExtremaCalculateBadness": "bool",
    "RedArrowExtremaIgnoreBadnessBelow": "float",
    "RedArrowSmoothMaxDistance": "float",
    "RedArrowCheckFractionalIgnorePointZero": "bool",
    "RedArrowCollinearMaxDistance": "float",
    "RedArrowGridLength": "int",
    "RedArrowInflectionMin": "float",
    "RedArrowSpikeAngle": "float",
}


def nsc(r: float, g: float, b: float, a: float) -> NSColor:
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


def nsc_arch(r: float, g: float, b: float, a: float):
    result, _err = (
        NSKeyedArchiver.archivedDataWithRootObject_requiringSecureCoding_error_(
            nsc(r, g, b, a), True, None
        )
    )
    return result


def typechecked_options(
    options: "RedArrowOptionsDict",
) -> RedArrowOptionsDict:
    out: RedArrowOptionsDict = {}
    for k, v in default_options.items():
        t = option_types.get(k, "float")
        if t == "bool":
            out[k] = bool(options.get(k, v))
        elif t == "float":
            v = options.get(k, v)
            if isinstance(v, NSDecimalNumber):
                out[k] = v.floatValue()
            elif isinstance(
                v, (objc._pythonify.OC_PythonFloat, objc._pythonify.OC_PythonLong)
            ):
                out[k] = float(v)
            elif isinstance(v, (float, int)):
                out[k] = v
            else:
                print(
                    f"Unknown type for {k}: '{type(v)}', using default value: {default_options[k]}"
                )
        elif t == "int":
            out[k] = int(v)
        else:
            print(
                f"Unknown type for {k}: '{type(v)}', using default value: {default_options[k]}"
            )

    return out
