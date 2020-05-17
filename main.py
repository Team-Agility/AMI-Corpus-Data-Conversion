import xml.etree.ElementTree as ET
from playsound import playsound
import time
import glob
import os
import shutil

def GetAllMeetingIDs():
  return [ os.path.basename(folder_path) for folder_path in glob.glob(f'amicorpus/ES*')]

class Audio:
  def __init__(self, meeting_id):
    self.meeting_id = meeting_id

  def get_speaker(self, agent):
    meetings_meta_root = ET.parse('AMI manual annotations v1.6.2/corpusResources/meetings.xml').getroot()
    for speaker in meetings_meta_root.iter('speaker'):
      if speaker.get('{http://nite.sourceforge.net/}id').startswith(self.meeting_id) and speaker.get('nxt_agent') == agent:
        return {
          'global_name': speaker.get('global_name'),
          'role': speaker.get('role')
        }

  def path(self):
    return f'amicorpus/{self.meeting_id}/audio/{self.meeting_id}.Mix-Headset.wav'

  def play(self):
    print(f'Playing {self.meeting_id} ....')
    playsound(self.path(), False)

  def transcript_xmls(self):
    file_paths = {}
    for file_path in glob.glob(f'AMI manual annotations v1.6.2/words/{self.meeting_id}*'):
      file_paths[os.path.basename(file_path).split('.')[1]] = ET.parse(file_path).getroot()
    return file_paths

  def print_meeting_metadata(self):
    print(f'------------ Meeting: {self.meeting_id} --------------')
    transcript_file_paths = self.transcript_xmls()
    for agent in transcript_file_paths.keys():
      speaker = self.get_speaker(agent)
      print(f"Agent ID: {agent}, Global Name: {speaker['global_name']}, Role: {speaker['role']}")

  def print_transcript(self):   
    print(f'\n--------------- Transcript -----------------')
    timer = time.time() 
    transcript_file_paths = self.transcript_xmls()
    while True:
      for agent, root in transcript_file_paths.items():
        for word in root.findall('w'):
          time_escaped = time.time() - timer
          starttime = float(word.get('starttime'))
          endtime = float(word.get('endtime'))
          #is_punction = bool(word.get('punc'))
          content = word.text
          if time_escaped <= starttime and time_escaped +1 >= starttime:
            print(f'{agent}:', starttime, endtime, content)
      time.sleep(1)

all_meeting_ids = GetAllMeetingIDs()
for meeting_id in all_meeting_ids:
  meeting = Audio(meeting_id)
  meeting.play()
  meeting.print_meeting_metadata()
  meeting.print_transcript()