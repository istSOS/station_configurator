# Station Configurator

Easy-to-use configurator to monitor environmental parameters with professional instruments

# Requirements

1. istSOS installed locally (www.istsos.org)
2. Python 3
3. Python 3 pip
4. Supported instruments:
    - Ponsel instruments with ModBus 485 communication protocol
    - Lufft compact weather station WS-501 with ModBus 485 communication protocol
    - Unilux by Chelsea Technologies with RS232 communication protocol
    - Trilux by Chelsea Technologies with RS232 communication protocol
5. Raspberry pi or other Linux device with a ModBus compatible port

# How to use

1. Clone the repository

        ```bash
        git clone https://gitlab.com/danistrigaro/station_configurator.git
        ```

2. Very important to disable ModemManager module otherwise USB serial communication is not reliable
        ```bash
        sudo systemctl disable ModemManager
        ```

3. Install postgresql-client

        ```bash
        sudo apt install build-essential
        sudo apt install postgresql-client
        sudo apt install python3-dev libpq-dev
        sudo apt-get install libxml2-dev libxslt1-dev
        ```

4. Navigate inside the repository's folder

        ```bash
        cd station_configurator/
        ```

5. Install the *requirements.txt* using pip

        ```bash
        pip install -r requirements.txt
        ```

6. Edit and configure the section **DEFAULT** in the file *default.cfg*. Hereinafter each parameter is explained:

    - **transmission**: one of
        - *nb-iot*: LTE CAT1/NB-IoT: (default)
        - *lora*: LoRaWAN(default)
        - *serial*: Serial (to be implemented)
        - *wifi*: WiFi (to be implemented)

        This setting defined how to transmit data to the data center.
    - **istsos**: str
        - *http://localhost/istsos*: url of istSOS (*default*)

        This istSOS url identified the instance where the raw and aggregated data can be archived.
    - **service**: str
        - *station*: name of the istSOS service where raw data are archived (*default*)
    - **user**: str
        - *admin*: user to access istSOS. The user must have the read and write permissions
    - **password**: str
        - *batman*: password of the istSOS user (*default*)
    - **log**: one of
        - *DEBUG* (*default*)
        - *INFO*
        - *ERROR*
    - **max_log_days**: int
        - *20*: max period for logged values (*default*)
    - **sending_time**: int
        - *20*: every (*default*)
    - **remote_istsos**: str
        - http://istsos.org/istsos
    - **remote_service**: str
        - demo
    - **remote_user**: str
        - admin
    - **remote_password**: str
        - batmnan

    Example:

        ```
        [DEFAULT]
        transmission = serial
        istsos = http://localhost/istsos
        service = demo
        user = admin
        password = batman
        log = DEBUG
        max_log_days = 20
        sending_time = 20
        remote_istsos = http://localhost/istsos
        remote_service = demo
        remote_user = admin
        remote_password = batman
        ```

7. In the *default.cfg* file add as many sections as sensors you have. Take a look into the point 6 to have more information.

    **N.B. 1: if you are using a single MODBUS port to connect more than one sensor remember to use the same *sampling_time* number** 

    **N.B. 2: if you are using a single MODBUS port to connect more than one sensor and if you are using more than one sensor of the same type, so with the same address, remember to configure different address for each sensor before start with the configuration**

8. The name of the section will give the name to the sensor which will be register into the istSOS

9. fix a astatic usb path https://rolfblijleven.blogspot.com/2015/02/howto-persistent-device-names-on.html
