import xml.etree.ElementTree as ET
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
    self.words = {}
    self._init_words_tracker()

    self.da_types = {}
    self.dialog_acts = {}
    self._init_da_types()

    self.dest_folder = f'{DATASET_OUT_DIR}/{self.meeting_id}'
    os.makedirs(self.dest_folder, exist_ok=True)


  def _init_words_tracker(self):
    transcript_file_xml = self.get_transcript_xml_roots()
    for agent, root in transcript_file_xml.items():
      self.agents.append(agent)
      self.words_count[agent] = len(transcript_file_xml[agent].findall('w'))
      self.words_tracker[agent] = {}
      for word in root.findall('w'):
        self.words_tracker[agent][word.get(NITE_ID)] = False
        self.words[word.get(NITE_ID)] = word

  def _init_da_types(self):
    da_types_root = ET.parse(f'{AMI_DATASET_DIR}/ontologies/da-types.xml').getroot()
    for da_type in da_types_root:
      self.da_types[da_type.get(NITE_ID)] = {
        'main_type': da_type.get('gloss'),
        'sub_type': None
      }
      for da_type_child in da_type:
        self.da_types[da_type_child.get(NITE_ID)] = {
        'main_type': da_type.get('gloss'),
        'sub_type': da_type_child.get('gloss')
      }

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
    transcript_file_xml = self.get_transcript_xml_roots()
    for agent in transcript_file_xml.keys():
      speaker = self.get_participant_meta(agent)
      transcript_word_count = meeting.get_transcript_word_count(agent)
      print(f"Agent ID: {agent}, Global Name: {speaker['global_name']}, Role: {speaker['role']}, Sex: {speaker['sex']}, Age: {speaker['age']}, Native Language: {speaker['native_language']}, Region: {speaker['region']}, Total Words in Transcript: {transcript_word_count}")

  def print_transcript(self):   
    print(f'--------------- Transcript -----------------')
    timer = time.time() 
    transcript_file_xml = self.get_transcript_xml_roots()
    while True:
      for agent, root in transcript_file_xml.items():
        for word in root.findall('w'):
          time_escaped = time.time() - timer
          start_time = float(word.get('starttime'))
          end_time = float(word.get('endtime'))
          #is_punction = bool(word.get('punc'))
          content = word.text
          if time_escaped <= start_time and time_escaped +1 >= start_time:
            print(f'{agent}:', start_time, end_time, content)
      time.sleep(1)

  def copy_audio_dataset(self):
    print(f'Copying Audio: {self.meeting_id} ...')

    src_audio_path = self.get_audio_path()
    dest_audio_path = f'{self.dest_folder}/audio.wav'
    shutil.copyfile(src_audio_path, dest_audio_path)
    print()

  def convert_transcript_to_json(self):
    print(f'Converting Transcript {self.meeting_id} ...')

    transcript = {
      'transcript': [],
      'speakers': {}
    }
    
    transcript_file_xml = self.get_transcript_xml_roots()
    for agent, root in transcript_file_xml.items():
      transcript['speakers'][agent] = self.get_participant_meta(agent)
      for word in root.findall('w'):
        if not word.get('starttime'):
          continue
        id = word.get(NITE_ID)
        start_time = float(word.get('starttime'))
        end_time = float(word.get('endtime'))
        is_punction = bool(word.get('punc'))
        content = word.text

        if self.words_tracker[agent][id]:
          input(colored(f'Word {id} Already Converted. \nPress any key to continue...', 'yellow'))
          
        self.words_tracker[agent][id] = True
        transcript['transcript'].append({
          'speaker_id': agent,
          'start_time': start_time,
          'end_time': end_time,
          'content': content,
          'is_punction': is_punction
        })
        
    if len(transcript['transcript']) != sum(self.words_count.values()):
      input(colored(f'Error in Word Count. Missing {sum(self.words_count.values()) - len(transcript["transcript"])} Words. \nPress any key to continue...', 'yellow'))

    with open(f'{self.dest_folder}/transcript.json', 'w') as fp:
      json.dump(transcript, fp, sort_keys=True, indent=2)

  def get_dialog_act_xml_roots(self):
    file_paths = {}
    for file_path in glob.glob(f'{AMI_DATASET_DIR}/dialogueActs/{self.meeting_id}*'):
      file_paths[os.path.basename(file_path).split('.')[1]] = ET.parse(file_path).getroot()
    return file_paths

  def get_word_by_id(self, id):
    meeting_id = id.strip().split('.')[0]
    if meeting_id != self.meeting_id:
      input(colored('Invalid Meeting ID', 'red'))
    
    if id in self.words:
      return self.words[id]
    return False

  def get_words_by_range(self, word_range_href):
    start_time = 99999999.99
    end_time = 0.00
    word_range = word_range_href.split('#')[1].split('..')
    word_id_prefix = '.'.join(word_range[0].replace('id(', '').replace(')', '').split('.')[0:-1])
    if len(word_range) < 2:
      word_range.append(word_range[0])
    start, end = map(int, [word_no.replace('id(', '').replace(')', '').split('.')[-1].replace('words', '') for word_no in word_range])
    
    act = ''
    for i in range(start, end+1):
      word_xml = self.get_word_by_id(f'{word_id_prefix}.words{i}')
      if word_xml == False:
        continue
      if not bool(word_xml.get('punc')) and len(act) > 0:
        act += ' '
      act += word_xml.text
      if start_time > float(word_xml.get('starttime')):
        start_time = float(word_xml.get('starttime'))
      if end_time < float(word_xml.get('endtime')):
        end_time = float(word_xml.get('endtime'))
    if act == '':
      return [False, start_time, end_time]
    return [act, start_time, end_time]

  def convert_dialog_acts_to_json(self):
    print(f'Converting Dialog Act {self.meeting_id} ...')

    dialog_acts = {
      'acts': [],
      'speakers': {}
    }
    
    transcript_file_xml = self.get_dialog_act_xml_roots()
    for agent, root in transcript_file_xml.items():
      dialog_acts['speakers'][agent] = self.get_participant_meta(agent)
      for act_xml in root.findall('dact'):
        act_data = {
          'id': int(act_xml.get(NITE_ID).split('.')[-1]),
          'speaker_id': agent
        }
        da_type = act_xml.find('{http://nite.sourceforge.net/}pointer')
        words = act_xml.find('{http://nite.sourceforge.net/}child')
        
        if da_type is not None:
          act_data['type'] = self.da_types[da_type.get('href').split('#')[1].replace('id(', '').replace(')', '')]
        if words is not None:
          act, start_time, end_time = self.get_words_by_range(words.get('href'))          
          if not act:
            continue

          act_data['act'] = act
          act_data['start_time'] = start_time
          act_data['end_time'] = end_time
          self.dialog_acts[act_xml.get(NITE_ID)] = act_data
        dialog_acts['acts'].append(act_data)

    with open(f'{self.dest_folder}/dialog_acts.json', 'w') as fp:
      json.dump(dialog_acts, fp, sort_keys=True, indent=2)

  def get_dialog_acts_by_range(self, dialog_act_range_href):
    dialog_act_range = dialog_act_range_href.split('#')[1].split('..')
    dialog_act_id_prefix = '.'.join(dialog_act_range[0].replace('id(', '').replace(')', '').split('.')[0:-1])
    if len(dialog_act_range) < 2:
      dialog_act_range.append(dialog_act_range[0])
    start, end = map(int, [dialog_act_no.replace('id(', '').replace(')', '').split('.')[-1].replace('dialog-act', '') for dialog_act_no in dialog_act_range])
    
    dialog_acts = ''
    for i in range(start, end+1):
      if f'{dialog_act_id_prefix}.{i}' not in self.dialog_acts:
        continue
      dialog_act_xml = self.dialog_acts[f'{dialog_act_id_prefix}.{i}']['act']
      if dialog_act_xml == False:
        continue
      if len(dialog_acts) > 0:
        dialog_acts += ' '
      dialog_acts += dialog_act_xml
    if dialog_acts == '':
      return False
    return dialog_acts


  def convert_extractive_summary_to_json(self):
    print(f'Converting Extractive Summary {self.meeting_id} ...')

    ext_summs = []
    ext_summ_file_xml = ET.parse(f'{AMI_DATASET_DIR}/extractive/{meeting_id}.extsumm.xml').getroot()

    for ext_summ in ext_summ_file_xml:
      for dialog_act_xml in ext_summ.findall('{http://nite.sourceforge.net/}child'):
        dialog_act_href = dialog_act_xml.get('href')
        dialog_act = self.get_dialog_acts_by_range(dialog_act_href)        
        
        dialog_act_range = dialog_act_href.split('#')[1].split('..')
        if len(dialog_act_range) < 2:
          dialog_act_range.append(dialog_act_range[0])
        start, end = map(int, [dialog_act_no.replace('id(', '').replace(')', '').split('.')[-1].replace('dialog-act', '') for dialog_act_no in dialog_act_range])

        ext_summ = self.dialog_acts[dialog_act_range[0].replace('id(', '').replace(')', '')]
        main_type = None
        sub_type = None
        if 'type' in ext_summ:
          main_type = ext_summ['type']['main_type']
          sub_type = ext_summ['type']['sub_type']
        ext_summs.append({
          'dialog_act': dialog_act,
          'speaker_id': dialog_act_range[0].replace('id(', '').replace(')', '').split('.')[1],
          'dialog_act_start_id': start,
          'dialog_act_end_id': end,
          'type': {
            'main_type': main_type,
            'sub_type': sub_type
          }
        })

    with open(f'{self.dest_folder}/extractive_summary.json', 'w') as fp:
      json.dump(ext_summs, fp, sort_keys=True, indent=2)

  def convert_abstractive_summary_to_json(self):
    print(f'Converting Abstractive Summary {self.meeting_id} ...')

    abs_summs = {
      'abstract': [],
      'actions': [],
      'decisions': [],
      'problems': []
    }
    
    abs_summ_file_xml = ET.parse(f'{AMI_DATASET_DIR}/abstractive/{meeting_id}.abssumm.xml').getroot()

    for abstract in abs_summ_file_xml.find('abstract').findall('sentence'):
      abs_summs['abstract'].append(abstract.text)
    for action in abs_summ_file_xml.find('actions').findall('sentence'):
      abs_summs['actions'].append(action.text)
    for decision in abs_summ_file_xml.find('decisions').findall('sentence'):
      abs_summs['decisions'].append(decision.text)
    for problem in abs_summ_file_xml.find('problems').findall('sentence'):
      abs_summs['problems'].append(problem.text)

    with open(f'{self.dest_folder}/abstractive_summary.json', 'w') as fp:
      json.dump(abs_summs, fp, sort_keys=True, indent=2)


all_meeting_ids = GetAllMeetingIDs()
for meeting_id in all_meeting_ids:
  meeting = Meeting(meeting_id)
  meeting.print_meeting_metadata()
  meeting.copy_audio_dataset()
  meeting.convert_transcript_to_json()
  meeting.convert_dialog_acts_to_json()
  meeting.convert_extractive_summary_to_json()
  meeting.convert_abstractive_summary_to_json()