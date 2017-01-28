import glob
import os
import sys
import select
import subprocess
import pymysql as mysql

import cv2

import config
import face
import train


# Prefix for positive training image filenames.
POSITIVE_FILE_PREFIX = 'positive_'
owd = os.getcwd()


def is_letter_input(letter):
    # Utility function to check if a specific character is available on stdin.
    # Comparison is case insensitive.
    if select.select([sys.stdin,],[],[],0.0)[0]:
        input_char = sys.stdin.read(1)
        return input_char.lower() == letter.lower()
    return False


if __name__ == '__main__':
    camera = config.get_camera()
    user = input("Name (first and last) of subject: ")
    user_name = (user.split(' ')[1])+", "+(user.split(' ')[0])
    print(user_name)
    userfolder = config.POSITIVE_DIR+"/"+user.lower().replace(" ", "_")
    # Create the directory for positive training images if it doesn't exist.
    if not os.path.exists(userfolder):
        os.makedirs(userfolder)
        userlist = open("user_list.txt", "a")
        userlist.write(","+user.lower().replace(" ","_"))
        userlist.close()
    # Find the largest ID of existing positive images.
    # Start new images after this ID value.
    files = sorted(glob.glob(os.path.join(userfolder, 
        POSITIVE_FILE_PREFIX + '[0-9][0-9][0-9].pgm')))
    count = 0
    if len(files) > 0:
        # Grab the count from the last filename.
        count = int(files[-1][-7:-4])+1
    print('Capturing positive training images.')
    print('Type c (and press enter) to capture an image.')
    print ('Press Ctrl-C to quit.')
    while count < 10:
        # Check if button was pressed or 'c' was received, then capture image.
        if is_letter_input('c'):
            print('Capturing image %i of 10' % (count,))
            image = camera.read()
            # Convert image to grayscale.
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            # Get coordinates of single face in captured image.
            result = face.detect_single(image)
            if result is None:
                print('Could not detect single face!  Check the image in capture.pgm' \
                      ' to see what was captured and try again with only one face visible.')
                continue
            x, y, w, h = result
            # Crop image as close as possible to desired face aspect ratio.
            # Might be smaller if face is near edge of image.
            crop = face.crop(image, x, y, w, h)
            # Save image to file.
            filename = os.path.join(userfolder, POSITIVE_FILE_PREFIX + '%03d.pgm' % count)
            cv2.imwrite(filename, crop)
            print('Found face and wrote training image', filename)
            count += 1

    print("finished capturing images! processing...")
    train.Train(user)
    print ("finished processing. user '%s' added" % (user,))

    os.chdir(owd)
    
    print ("touch user's card to reader now for database acquisition")
    rfidproc = subprocess.Popen('python RFID-process.py', shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    (output, errors) = rfidproc.communicate()
    
    card_id = output.split(':')[-1][:-1]
    print("read card id:",card_id)
    

    db = mysql.connect(host="localhost",user="monitor",passwd="raspberry",db="Attendance")
    cur = db.cursor()
    query = 'INSERT into users (card_id, user_name) VALUES ("'+card_id+'", "'+user_name+'");'
    cur.execute(query)
    db.commit()

    print ('user committed to database. exiting!')
    exit()