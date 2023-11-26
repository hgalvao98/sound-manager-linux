import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import subprocess
import re
from locale import atof, setlocale, LC_NUMERIC

def get_pactl_output(command):
    result = subprocess.run(command, shell=True, capture_output=True)
    return result.stdout.decode('utf-8')

def parse_pactl_output(output):
    devices = {}
    current_device = None
    parsing_properties = False

    setlocale(LC_NUMERIC, 'C')

    for line in output.splitlines():
        if line.startswith('Destino #'):
            if current_device:
                devices[current_device['name']] = current_device
            current_device = {'name': line[len('Destino #'):].strip(), 'properties': {}}
            parsing_properties = False
        elif line.startswith('\t'):
            if current_device:
                key, _, value = map(str.strip, line.strip().partition(':'))
                if key == 'Volume':
                    volumes = re.findall(r'(\S+): (\d+) / (\d+)% / ([\-\d,.]+) dB', value)
                    current_device['volumes'] = {name: {'value': int(val), 'percentage': int(percentage), 'db': atof(db.replace(',', '.'))}
                                                 for name, val, percentage, db in volumes}
                elif key == 'Portas':
                    current_device['ports'] = re.findall(r'\[([^\]]+)\]: (.+?) \((.*?)\)', value)
                else:
                    current_device[key.lower()] = value
        elif line.startswith('Propriedades:'):
            parsing_properties = True
        elif parsing_properties and line.strip():
            key, _, value = map(str.strip, line.partition('='))
            current_device['properties'][key] = value

    if current_device:
        devices[current_device['name']] = current_device

    # Reset the locale
    setlocale(LC_NUMERIC, '')

    return devices

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, devices, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        menu = QtWidgets.QMenu(parent)
        outputDevicesMenu = menu.addMenu("Output Devices")
        inputDevicesMenu = menu.addMenu("Input Devices Coming Soon")
        inputDevicesMenu.setEnabled(False)
        actionGroup = QtWidgets.QActionGroup(self)  
        for device in devices.values():
            deviceAction = QtWidgets.QAction(device['descrição'], self, checkable=True)
            if device['estado'] == 'RUNNING':
                deviceAction.setChecked(True)
            deviceAction.triggered.connect(lambda checked, device=device: self.device_selected(device, 'output'))
            actionGroup.addAction(deviceAction) 
            outputDevicesMenu.addAction(deviceAction) 

        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(self.exit)
        self.setContextMenu(menu)
        self.show()

    def device_selected(self, device, device_type):
        self.switch_audio_device(device, device_type)

    def switch_audio_device(self, device, device_type):
        index = device['name']
        command = f"pacmd set-default-sink {index}"
        subprocess.run(command, shell=True)


    def exit(self):
        self.hide()  # Hide the tray icon
        QtCore.QCoreApplication.exit()

def main(image):
    output = get_pactl_output("pactl list sinks")
    devices = parse_pactl_output(output)
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    trayIcon = SystemTrayIcon(QtGui.QIcon(image), devices, w)

    trayIcon.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main('lightThemeIcon.png')

