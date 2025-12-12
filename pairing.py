import panasonic_viera
rc = panasonic_viera.RemoteControl("192.168.60.85", proxy='http://192.168.30.16:8118')
# Make the TV display a pairing pin code
rc.request_pin_code()
# Interactively ask the user for the pin code
pin = input("Enter the displayed pin code: ")
# Authorize the pin code with the TV
rc.authorize_pin_code(pincode=pin)
# Display credentials (application ID and encryption key)
print(rc.app_id)
print(rc.enc_key)
# We can now start communicating with our TV
# Send EPG key
rc.send_key(panasonic_viera.Keys.epg)