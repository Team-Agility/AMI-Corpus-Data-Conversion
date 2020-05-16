import xml.etree.ElementTree as ET
from playsound import playsound
import time
import glob

class Audio:
  def __init__(self, meeting_id):
    self.meeting_id = meeting_id

  def path(self):
    return f'amicorpus/{self.meeting_id}/audio/{self.meeting_id}.Mix-Headset.wav'

  def play(self):
    playsound(self.path(), False)

  def transcript_xmls(self):
    file_paths = {}
    for file_path in glob.glob(f'xml/words/{self.meeting_id}*'):
      file_paths[file_path.split(f'{self.meeting_id}.')[1].split('.')[0]] = ET.parse(file_path).getroot()
    return file_paths

  def get_transcript(self):
    timer = time.time()
    transcript_file_paths = self.transcript_xmls()
    
    while True:
      for role, root in transcript_file_paths.items():
        for word in root.findall('w'):
          time_escaped = time.time() - timer
          starttime = float(word.get('starttime'))
          endtime = float(word.get('endtime'))
          content = word.text
          if time_escaped <= starttime and time_escaped +1 >= starttime:
            print(f'{role}:', starttime, endtime, content)
      time.sleep(1)

meeting1 = Audio('ES2002c')
meeting1.play()
meeting1.get_transcript()