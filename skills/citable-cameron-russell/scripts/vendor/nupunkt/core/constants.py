"""
Constants module for nupunkt.

This module provides constants used in the Punkt algorithm,
including orthographic context and cache configuration.
"""


# -------------------------------------------------------------------
# Orthographic Context Constants
# -------------------------------------------------------------------

# Bit flags for orthographic contexts
ORTHO_BEG_UC = 1 << 1  # Beginning of sentence, uppercase
ORTHO_MID_UC = 1 << 2  # Middle of sentence, uppercase
ORTHO_UNK_UC = 1 << 3  # Unknown position, uppercase
ORTHO_BEG_LC = 1 << 4  # Beginning of sentence, lowercase
ORTHO_MID_LC = 1 << 5  # Middle of sentence, lowercase
ORTHO_UNK_LC = 1 << 6  # Unknown position, lowercase

# Combined flags
ORTHO_UC = ORTHO_BEG_UC | ORTHO_MID_UC | ORTHO_UNK_UC  # Any uppercase
ORTHO_LC = ORTHO_BEG_LC | ORTHO_MID_LC | ORTHO_UNK_LC  # Any lowercase

# Mapping from (position, case) to flag
ORTHO_MAP: dict[tuple[str, str], int] = {
    ("initial", "upper"): ORTHO_BEG_UC,
    ("internal", "upper"): ORTHO_MID_UC,
    ("unknown", "upper"): ORTHO_UNK_UC,
    ("initial", "lower"): ORTHO_BEG_LC,
    ("internal", "lower"): ORTHO_MID_LC,
    ("unknown", "lower"): ORTHO_UNK_LC,
}

# -------------------------------------------------------------------
# Caching Constants
# -------------------------------------------------------------------

# LRU cache sizes for various caching operations
# These can be adjusted based on memory constraints and desired performance

# Cache size for abbreviation checks - moderate size as number of abbreviations is usually limited
ABBREV_CACHE_SIZE = 32768  # Power of 2 (2^15) - Increased 8x from 4096

# Cache size for token creation and property caching - larger as token variety is high
TOKEN_CACHE_SIZE = 262144  # Power of 2 (2^18) - critical for performance - Increased 8x from 32768

# Cache size for orthographic heuristics - frequently used so needs to be large
ORTHO_CACHE_SIZE = 65536  # Power of 2 (2^16) - Increased 8x from 8192

# Cache size for sentence starter checks - less variety than tokens
SENT_STARTER_CACHE_SIZE = 32768  # Power of 2 (2^15) - Increased 8x from 4096

# Cache size for token type calculations - moderate variety
TOKEN_TYPE_CACHE_SIZE = 131072  # Power of 2 (2^17) - Increased 8x from 16384

# Cache size for document-level tokenization results - benchmarks showed this is critical
DOC_TOKENIZE_CACHE_SIZE = 65536  # Power of 2 (2^16) - Increased 8x from 8192

# Cache size for paragraph-level caching in tokenizer - moderate usage
PARA_TOKENIZE_CACHE_SIZE = 65536  # Power of 2 (2^16) - Increased 8x from 8192

# Cache size for whitespace index lookups - pattern is less varied
WHITESPACE_CACHE_SIZE = 16384  # Power of 2 (2^14) - Increased 8x from 2048
