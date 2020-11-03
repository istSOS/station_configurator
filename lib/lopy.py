import time
import serial


def send_data(data):
  print(data)
  try:
      import RPi.GPIO as GPIO
  except Exception as e:
      print(str(e))
      return False
  try:
    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
    ser.flush()
    GPIO.setmode(GPIO.BOARD)
    mode = GPIO.getmode()


    GPIO.setup(7, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(1)
    cnt = 0
    received = ''
    while cnt <= 20:
        GPIO.output(7, GPIO.HIGH)
        if (ser.in_waiting > 0):
            received = ser.readline()
            print(received)
            if received == b'OK\n':
                break
        GPIO.output(7, GPIO.LOW)
        time.sleep(1)
        cnt+=1

    sent = 0
    if received==b'OK\n':
        for row in data:
            cnt = 0
            print('sending {}'.format(row))
            ser.write(
              'SEND {}\n'.format(row).encode()
            )
            while cnt <= 20:
                if (ser.in_waiting > 0):
                  received = ser.readline()
                  print(received)
                  if received==b'SENT\n':
                      print('Data sent')
                      sent+=1
                      break
                time.sleep(1)
                cnt+=1

    ser.write(b'STOP')

    time.sleep(0.1)

    GPIO.setup(7, GPIO.OUT, initial=GPIO.LOW)
    GPIO.cleanup()
    if sent == len(data):
      return True
    else:
      return False
  except:
    GPIO.cleanup()
    return False