import time
import progressbar

class ProgBar:
    def __init__(self, start_message):
        self.value = 1
        self.format_custom_text = progressbar.FormatCustomText('Status: %(status_message)50s',{'status_message': start_message})
        self.bar = progressbar.ProgressBar(max_value=20, widgets=[progressbar.Timer(), progressbar.AnimatedMarker(), progressbar.Bar(),progressbar.Percentage(),self.format_custom_text])
        self.bar.update(self.value)
    def tick(self, message):
        self.value += 1
        self.bar.update(self.value)
        self.format_custom_text.update_mapping(status_message=message)

bar = ProgBar("start")

for i in range(20):
    bar.tick('test')
    time.sleep(1)