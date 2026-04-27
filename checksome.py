import hashlib
from util.config import slangApiSalt, slangApiKey
 
def generate_checksum(action, slangApiKey, text, slangApiSalt):
    check_string = f"{action}:{slangApiKey}:{text}:{slangApiSalt}"
    checksum = hashlib.sha512(check_string.encode()).hexdigest()
    return checksum