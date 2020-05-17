import xml.etree.ElementTree as ET
from playsound import playsound
from termcolor import colored
import time
import glob
import os
import shutil
import json

os.system('color')

NITE_ID = '{http://nite.sourceforge.net/}id'
AMI_DATASET_DIR = 'AMI manual annotations v1.6.2'
DATASET_OUT_DIR = 'dataset'

def GetAllMeetingIDs():
  return [ os.path.basename(folder_path) for folder_path in glob.glob(f'amicorpus/ES*')]

class Meeting:
  def __init__(self, meeting_id):
    self.meeting_id = meeting_id
    self.words_tracker = {}
    self.words_count = {}
    self.agents = []
    self._init_words_tracker()

  def _init_words_tracker(self):
    transcript_file_paths = self.get_transcript_xml_roots()
    for agent, root in transcript_file_paths.items():
      self.agents.append(agent)
      self.words_count[agent] = len(transcript_file_paths[agent].findall('w'))
      self.words_tracker[agent] = {}
      for word in root.findall('w'):
        self.words_tracker[agent][word.get(NITE_ID)] = False

  def get_participant_meta(self, agent):
    meetings_meta_root = ET.parse(f'{AMI_DATASET_DIR}/corpusResources/meetings.xml').getroot()
    participants_meta_root = ET.parse(f'{AMI_DATASET_DIR}/corpusResources/participants.xml').getroot()
    for speaker in meetings_meta_root.iter('speaker'):
      if speaker.get(NITE_ID).startswith(self.meeting_id) and speaker.get('nxt_agent') == agent:
        participant_meta = {}
        for participant in participants_meta_root.iter('participant'):
          if participant.get(NITE_ID) == speaker.get('global_name') and self.meeting_id.startswith(participant.get('meeting')):
            participant_meta = dict(participant.items())
            participant_meta['region'] = participant[0].get('region')

        return {
          'global_name': speaker.get('global_name'),
          'role': speaker.get('role'),
          'sex': participant_meta['sex'],
          'age': int(float(participant_meta['age_at_collection'])) if 'age_at_collection' in participant_meta else None,
          'native_language': participant_meta['native_language'],
          'region': participant_meta['region']
        }

  def get_audio_path(self):
    return f'amicorpus/{self.meeting_id}/audio/{self.meeting_id}.Mix-Headset.wav'

  def play_audio(self):
    print(f'Playing {self.meeting_id} ....')
    playsound(self.get_audio_path(), False)

  def get_transcript_xml_roots(self):
    file_paths = {}
    for file_path in glob.glob(f'{AMI_DATASET_DIR}/words/{self.meeting_id}*'):
      file_paths[os.path.basename(file_path).split('.')[1]] = ET.parse(file_path).getroot()
    return file_paths

  def get_transcript_word_count(self, agent):
    if agent not in self.words_count:
      print('Invalid Agent')
      return None
    return self.words_count[agent]

  def print_meeting_metadata(self):
    print(f'\n\n------------ Meeting: {self.meeting_id} --------------')
    transcript_file_paths = self.get_transcript_xml_roots()
    for agent in transcript_file_paths.keys():
      speaker = self.get_participant_meta(agent)
      transcript_word_count = meeting.get_transcript_word_count(agent)
      print(f"Agent ID: {agent}, Global Name: {speaker['global_name']}, Role: {speaker['role']}, Sex: {speaker['sex']}, Age: {speaker['age']}, Native Language: {speaker['native_language']}, Region: {speaker['region']}, Total Words in Transcript: {transcript_word_count}")

  def print_transcript(self):   
    print(f'\n--------------- Transcript -----------------')
    timer = time.time() 
    transcript_file_paths = self.get_transcript_xml_roots()
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

  def copy_audio_dataset(self):
    print(f'Copying Audio: {self.meeting_id} ...')

    dest_folder = f'{DATASET_OUT_DIR}/{self.meeting_id}'
    os.makedirs(dest_folder, exist_ok=True)
    src_audio_path = self.get_audio_path()
    dest_audio_path = f'{dest_folder}/audio.wav'
    shutil.copyfile(src_audio_path, dest_audio_path)
    print()

  def convert_transcript_to_json(self):  
    print(f'Converting Transcript {self.meeting_id} ...')

    transcript = {
      'transcript': [],
      'speakers': {}
    }
    dest_folder = f'{DATASET_OUT_DIR}/{self.meeting_id}'
    transcript_file_paths = self.get_transcript_xml_roots()
    for agent, root in transcript_file_paths.items():
      transcript['speakers'][agent] = self.get_participant_meta(agent)
      for word in root.findall('w'):
        if not word.get('starttime'):
          continue
        id = word.get(NITE_ID)
        starttime = float(word.get('starttime'))
        endtime = float(word.get('endtime'))
        is_punction = bool(word.get('punc'))
        content = word.text

        if self.words_tracker[agent][id]:
          input(colored(f'Word {id} Already Converted. \nPress any key to continue...', 'yellow'))
          
        self.words_tracker[agent][id] = True
        transcript['transcript'].append({
          'speaker_id': agent,
          'starttime': starttime,
          'endtime': endtime,
          'content': content,
          'is_punction': is_punction
        })
        
    if len(transcript['transcript']) != sum(self.words_count.values()):
      input(colored(f'Error in Word Count. Missing {sum(self.words_count.values()) - len(transcript["transcript"])} Words. \nPress any key to continue...', 'yellow'))

    with open(f'{dest_folder}/transcript.json', 'w') as fp:
      json.dump(transcript, fp, sort_keys=True, indent=2)

all_meeting_ids = GetAllMeetingIDs()
for meeting_id in all_meeting_ids:
  meeting = Meeting(meeting_id)
  meeting.print_meeting_metadata()
  #meeting.copy_audio_dataset()
  meeting.convert_transcript_to_json()