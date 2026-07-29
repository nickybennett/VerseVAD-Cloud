"""Versioned, source-specific lexicon adapters."""

from versevad.adapters.base import (
    EmotionAssociationAdapter,
    EmotionIntensityAdapter,
    LexiconAdapterError,
    VadLexiconAdapter,
)
from versevad.adapters.concreteness import (
    BrysbaertConcretenessAdapter,
    ConcretenessAdapterError,
    ConcretenessEntry,
    ConcretenessLexicon,
    ConcretenessValidation,
)
from versevad.adapters.kuperman_aoa import (
    KupermanAoAAdapter,
    KupermanAoAAdapterError,
    KupermanAoAEntry,
    KupermanAoALexicon,
    KupermanAoAValidation,
)
from versevad.adapters.lancaster_sensorimotor import (
    LancasterSensorimotorAdapter,
    LancasterSensorimotorAdapterError,
    LancasterSensorimotorLexicon,
    LancasterSensorimotorValidation,
    SensorimotorEntry,
    SensorimotorVector,
)
from versevad.adapters.cmudict import (
    CMUDictAdapter,
    CMUDictAdapterError,
    CMUDictEntry,
    CMUDictLexicon,
    CMUDictValidation,
    CMUPronunciation,
    normalize_pronunciation_key,
)
from versevad.adapters.nrc_emotion import NrcEmotionAdapter
from versevad.adapters.nrc_intensity import NrcEmotionIntensityAdapter
from versevad.adapters.nrc_vad import NrcVadV1Adapter, NrcVadV21Adapter
from versevad.adapters.subtlex_us import (
    SubtlexUsAdapter,
    SubtlexUsAdapterError,
    SubtlexUsEntry,
    SubtlexUsLexicon,
    SubtlexUsValidation,
)
from versevad.adapters.warriner import WarrinerVadAdapter

__all__ = [
    "BrysbaertConcretenessAdapter",
    "ConcretenessAdapterError",
    "ConcretenessEntry",
    "ConcretenessLexicon",
    "ConcretenessValidation",
    "EmotionAssociationAdapter",
    "EmotionIntensityAdapter",
    "LexiconAdapterError",
    "KupermanAoAAdapter",
    "KupermanAoAAdapterError",
    "KupermanAoAEntry",
    "KupermanAoALexicon",
    "KupermanAoAValidation",
    "LancasterSensorimotorAdapter",
    "LancasterSensorimotorAdapterError",
    "LancasterSensorimotorLexicon",
    "LancasterSensorimotorValidation",
    "CMUDictAdapter",
    "CMUDictAdapterError",
    "CMUDictEntry",
    "CMUDictLexicon",
    "CMUDictValidation",
    "CMUPronunciation",
    "normalize_pronunciation_key",
    "NrcEmotionAdapter",
    "NrcEmotionIntensityAdapter",
    "NrcVadV1Adapter",
    "NrcVadV21Adapter",
    "SubtlexUsAdapter",
    "SubtlexUsAdapterError",
    "SubtlexUsEntry",
    "SubtlexUsLexicon",
    "SubtlexUsValidation",
    "SensorimotorEntry",
    "SensorimotorVector",
    "VadLexiconAdapter",
    "WarrinerVadAdapter",
]
