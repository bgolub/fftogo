import random
import string
import hashlib

def gen_hash(password, salt):
    h = hashlib.new('sha1')
    h.update(password)
    h.update(salt)
    hash = h.hexdigest()
    
    return hash
    
    
def gen_salt():
    salt = ''
    chars = string.letters + string.digits
    
    for i in range(5):
            salt += random.choice(chars)
            
    return salt