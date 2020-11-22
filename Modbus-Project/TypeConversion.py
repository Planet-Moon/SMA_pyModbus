from math import floor

def list_to_number(number, length=2, signed=False): #little endian
    unsigned_number = 0
    number_length = len(number)-1
    for i in range(number_length, -1, -1):
        factor = pow(2,16*(number_length-i))
        unsigned_number += number[i] * factor
        pass
    if not signed:
        return unsigned_number
    else:
        mask = 1 << 15 + number_length * 16
        if unsigned_number & mask:
            signed_Number = unsigned_number - ~mask
        else:
            signed_Number = unsigned_number & ~mask
        return signed_Number