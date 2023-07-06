import hashlib
import string
import datetime


ALPHANUMERIC_CHARS = string.ascii_letters + string.digits

def generate_alias(url):
  '''
  Generates a random 5 character string with alphanumeric characters, for example "3diw8"
  '''
  timestamp = datetime.datetime.now()
  unique_object = f"{url}/{timestamp}"

  hash_object = hashlib.md5(unique_object.encode())
  hash_string = hash_object.hexdigest()
  return hash_string[:5]
