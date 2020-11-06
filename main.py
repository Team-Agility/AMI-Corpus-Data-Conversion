import xml.etree.ElementTree as ET
from operator import itemgetter
from termcolor import colored
import time
import glob
import os
import shutil
import json

os.system('color')

NITE_ID = '{http://nite.sourceforge.net/}id'
NITE_POINTER = '{http://nite.sourceforge.net/}pointer'
NITE_CHILD = '{http://nite.sourceforge.net/}child'
AMI_DATASET_DIR = 'AMI manual annotations v1.6.2'
DATASET_OUT_DIR = 'dataset'
WARNINGS_COUNT = 0
ERROR_COUNT = 0

"""
  Get All Dataset's Meeting IDs
  
  :return: Strring Array with Meeting IDs
"""
def GetAllMeetingIDs():
  return [ os.path.basename(folder_path) for folder_path in glob.glob(f'amicorpus/ES*')]

class Meeting:
  def __init__(self, meeting_id):
    self.meeting_id = meeting_id
    self.metadata = {}

    self.words_tracker = {}
    self.words_count = {}
    self.agents = []
    self.words = {}
    self._init_words_tracker()

    self.da_types = {}
    self.dialog_acts = {}
    self._init_da_types()

    self.ae_types = {}
    self.argument_structs = {}
    self._init_ae_types()

    self.ar_types = {}
    self._init_ar_types()

    self.ap_types = {}
    self._init_ap_types()

    self.topics = {}
    self._init_topics()

    self.segments = {}

    self.summ_links = {}
    self.is_summ_links_initialized = False

    self.dest_folder = f'{DATASET_OUT_DIR}/{self.meeting_id}'
    os.makedirs(self.dest_folder, exist_ok=True)


  """
    Initiaize Words Tracker
  """
  def _init_words_tracker(self):
    transcript_file_xml = self.get_transcript_xml_roots()
    for agent, root in transcript_file_xml.items():
      self.agents.append(agent)
      self.words_count[agent] = len(transcript_file_xml[agent].findall('w'))
      self.words_tracker[agent] = {}
      for word in root.findall('w'):
        self.words_tracker[agent][word.get(NITE_ID)] = False
        self.words[word.get(NITE_ID)] = word

  """
    Initiaize Dialog Acts Types
  """
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

  """
    Initiaize Adjacency Pairs Types
  """
  def _init_ap_types(self):
    ap_types_root = ET.parse(f'{AMI_DATASET_DIR}/ontologies/ap-types.xml').getroot()
    for ap_type in ap_types_root.findall('ap-type'):
      self.ap_types[ap_type.get(NITE_ID)] = ap_type.get('gloss')

  """
    Initiaize Summary Links
  """
  def _init_summ_links(self):
    summ_links_root = ET.parse(f'{AMI_DATASET_DIR}/extractive/{self.meeting_id}.summlink.xml').getroot()
    for summ_link in summ_links_root.findall('summlink'):
      extractive_id = summ_link.find(".//*[@role='extractive']").get('href').split('#')[1].replace('id(', '').replace(')', '')
      abstractive_id = summ_link.find(".//*[@role='abstractive']").get('href').split('#')[1].replace('id(', '').replace(')', '')
      if abstractive_id not in self.summ_links:
        self.summ_links[abstractive_id] = {
          'types': {
            self.dialog_acts[extractive_id]['type']['sub_type']: 1
          },
          'abs': [self.dialog_acts[extractive_id]]
        }
      else:
        if 'type' in self.dialog_acts[extractive_id]:
          sub_type = self.dialog_acts[extractive_id]['type']['sub_type']
          if sub_type in self.summ_links[abstractive_id]['types']:
            self.summ_links[abstractive_id]['types'][sub_type] += 1
          else:
            self.summ_links[abstractive_id]['types'][sub_type] = 1
        self.summ_links[abstractive_id]['abs'].append(self.dialog_acts[extractive_id])

  """
    Check dialog act in Extractive Summary
  """
  def check_dialog_act_in_ext_summ(self, dialog_act_href):
    summ_links_root = ET.parse(f'{AMI_DATASET_DIR}/extractive/{self.meeting_id}.summlink.xml').getroot()
    for summ_link in summ_links_root.findall('summlink'):
      extractive_id = summ_link.find(".//*[@role='extractive']").get('href')
      #abstractive_id = summ_link.find(".//*[@role='abstractive']").get('href')
      if dialog_act_href == extractive_id:
        return True
    return False

  """
    Initiaize AE Types
  """
  def _init_ae_types(self):
    ae_types_root = ET.parse(f'{AMI_DATASET_DIR}/ontologies/ae-types.xml').getroot()
    for ae_type in ae_types_root.findall('ae-type'):
      self.ae_types[ae_type.get(NITE_ID)] = ae_type.get('gloss')

  """
    Initiaize AR Types
  """
  def _init_ar_types(self):
    ar_types_root = ET.parse(f'{AMI_DATASET_DIR}/ontologies/ar-types.xml').getroot()
    for ar_type in ar_types_root.findall('ar-type'):
      self.ar_types[ar_type.get(NITE_ID)] = ar_type.get('gloss')


  """
    Initiaize Topics
  """
  def _init_topics(self):    
    da_types_root = ET.parse(f'{AMI_DATASET_DIR}/ontologies/default-topics.xml').getroot()
    for topic in da_types_root.findall('topicname'):
      self.topics[topic.get(NITE_ID)] = topic.get('name')
      for sub_topic in topic.findall('topicname'):
        self.topics[sub_topic.get(NITE_ID)] = sub_topic.get('name')

  """
    Get Participant MetaData

    :param agent: Participant's Agent ID (A, B, C, D ...)
    :return: Participant Details dict with global_name, role, sex, age, native_language & region
  """
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

  """
    Get Meeting Audio Relative Path

    :return: Meeting Audio Relative Path
  """
  def get_audio_path(self):
    return f'amicorpus/{self.meeting_id}/audio/{self.meeting_id}.Mix-Headset.wav'

  """
    Get Word XML Roots

    :return: XML Root dict
  """
  def get_transcript_xml_roots(self):
    file_paths = {}
    for file_path in glob.glob(f'{AMI_DATASET_DIR}/words/{self.meeting_id}*'):
      file_paths[os.path.basename(file_path).split('.')[1]] = ET.parse(file_path).getroot()
    return file_paths

  """
    Get Segments XML Roots

    :return: XML Root dict
  """
  def get_segments_xml_roots(self):
    file_paths = {}
    for file_path in glob.glob(f'{AMI_DATASET_DIR}/segments/{self.meeting_id}*'):
      file_paths[os.path.basename(file_path).split('.')[1]] = ET.parse(file_path).getroot()
    return file_paths

  """
    Get Total words Count by Participent

    :param agent: Participant's Agent ID (A, B, C, D ...)
    :return: Number of Words
  """
  def get_transcript_word_count(self, agent):
    if agent not in self.words_count:
      print('Invalid Agent')
      return None
    return self.words_count[agent]

  """
    Print Meeting Participant MetaData
    * global_name, role, sex, age, native_language, region & Total Words in Transcript
  """
  def print_meeting_metadata(self):
    print(f'\n\n------------ Meeting: {self.meeting_id} --------------')
    transcript_file_xml = self.get_transcript_xml_roots()
    for agent in transcript_file_xml.keys():
      speaker = self.get_participant_meta(agent)
      transcript_word_count = meeting.get_transcript_word_count(agent)
      print(f"Agent ID: {agent}, Global Name: {speaker['global_name']}, Role: {speaker['role']}, Sex: {speaker['sex']}, Age: {speaker['age']}, Native Language: {speaker['native_language']}, Region: {speaker['region']}, Total Words in Transcript: {transcript_word_count}")

  """
    Print Meeting Words
    * Agent ID, Start Time, End Time, Word
  """
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

  """
    Copy Audio File to Output Folder
  """
  def copy_audio_dataset(self):
    print(f'Copying Audio: {self.meeting_id} ...')

    src_audio_path = self.get_audio_path()
    dest_audio_path = f'{self.dest_folder}/audio.wav'
    shutil.copyfile(src_audio_path, dest_audio_path)
    print()

  """
    Convert Words to JSON
  """
  def convert_transcript_to_json(self):
    print(f'Converting Transcript {self.meeting_id} ...')
    global WARNINGS_COUNT

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
          print(colored(f'Word {id} Already Converted. \nPress any key to continue...', 'yellow'))
          WARNINGS_COUNT += 1
          
        self.words_tracker[agent][id] = True
        transcript['transcript'].append({
          'speaker_id': agent,
          'start_time': start_time,
          'end_time': end_time,
          'content': content,
          'is_punction': is_punction
        })
        
    if len(transcript['transcript']) != sum(self.words_count.values()):
      print(colored(f'Error in Word Count. Missing {sum(self.words_count.values()) - len(transcript["transcript"])} Words. \nPress any key to continue...', 'yellow'))
      WARNINGS_COUNT += 1

    with open(f'{self.dest_folder}/transcript.json', 'w') as fp:
      json.dump(transcript, fp, sort_keys=True, indent=2)

  """
    Get Dialog Acts XML Roots

    :return: XML Root array
  """
  def get_dialog_act_xml_roots(self):
    file_paths = {}
    for file_path in glob.glob(f'{AMI_DATASET_DIR}/dialogueActs/{self.meeting_id}*.dialog-act.xml'):
      file_paths[os.path.basename(file_path).split('.')[1]] = ET.parse(file_path).getroot()
    return file_paths

  """
    Get Word By ID

    :param id: Word ID (XXXXXx.X.wordsx)
    :return: Word
  """
  def get_word_by_id(self, id):
    global ERROR_COUNT
    meeting_id = id.strip().split('.')[0]
    if meeting_id != self.meeting_id:
      print(colored('Invalid Meeting ID', 'red'))
      ERROR_COUNT += 1
    
    if id in self.words:
      return self.words[id]
    return False

  """
    Get Words By Range

    :param word_range_href: Word Range HREF (XXXXXXx.X.words.xml#id(XXXXXXx.X.wordsx)..id(XXXXXXx.X.wordsx))
    :return: dict with Dialog Act, Start Time & End Time
  """
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
      return {
      'act': False, 
      'start_time': start_time,
      'end_time': end_time
    }
    return {
      'act': act, 
      'start_time': start_time,
      'end_time': end_time
    }

  """
    Get Segments By Range

    :param segment_range_href: Word Range HREF (XXXXXXx.X.segments.xml#id(XXXXXXx.sync.xxx)..id(XXXXXXx.sync.xxx))
    :return: dict with Segment, Start Time & End Time
  """
  def get_segments_by_range(self, segment_range_href):
    start_time = 99999999.99
    end_time = 0.00
    segment_range = segment_range_href.split('#')[-1].split('..')
    segment_id_prefix = '.'.join(segment_range[0].replace('id(', '').replace(')', '').split('.')[0:-1])
    if len(segment_range) < 2:
      segment_range.append(segment_range[0])
    start, end = map(int, [segment_no.replace('id(', '').replace(')', '').split('.')[-1].replace('words', '') for segment_no in segment_range])
    
    segment = ''
    for i in range(start, end+1):
      if f'{segment_id_prefix}.{i}' not in self.segments:
        continue
      segment_tmp = self.segments[f'{segment_id_prefix}.{i}']
      if len(segment) > 0:
        segment += ' '
      segment += segment_tmp['segment']
      if start_time > segment_tmp['start_time']:
        start_time = segment_tmp['start_time']
      if end_time < segment_tmp['end_time']:
        end_time = segment_tmp['end_time']
    if segment == '':
      return {
      'segment': False, 
      'start_time': start_time,
      'end_time': end_time
    }
    return {
      'segment': segment, 
      'start_time': start_time,
      'end_time': end_time
    }

  """
    Convert Dialog Acts to JSON
  """
  def convert_dialog_acts_to_json(self):
    print(f'Converting Dialog Act {self.meeting_id} ...')
    self.metadata['da'] = {
      'types': {}
    }
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
        da_type = act_xml.find(NITE_POINTER)
        words = act_xml.find(NITE_CHILD)
        
        if da_type is not None:
          act_data['type'] = self.da_types[da_type.get('href').split('#')[1].replace('id(', '').replace(')', '')]
        if words is not None:
          act, start_time, end_time = itemgetter('act', 'start_time', 'end_time')(self.get_words_by_range(words.get('href')))          
          if not act:
            continue

          act_data['act'] = act
          act_data['start_time'] = start_time
          act_data['end_time'] = end_time
          self.dialog_acts[act_xml.get(NITE_ID)] = act_data
        dialog_acts['acts'].append(act_data)

        if 'type' not in dialog_acts['acts'][-1]:
          continue
        sub_type = dialog_acts['acts'][-1]['type']['sub_type']
        if sub_type in self.metadata['da']['types']:
          self.metadata['da']['types'][sub_type] += 1
        else:
          self.metadata['da']['types'][sub_type] = 1

    self.metadata['dialog_acts'] = len(self.dialog_acts)
    with open(f'{self.dest_folder}/dialog_acts.json', 'w') as fp:
      json.dump(dialog_acts, fp, sort_keys=True, indent=2)

  """
    Get Dialog Acts By Range

    :param dialog_act_range_href: Dialog Act Range HREF (XXXXXXa.X.dialog-act.xml#id(XXXXXXa.X.dialog-act.dharshi.x))
    :return: Array with Dialog Act, Start Time, End Time
  """
  def get_dialog_acts_by_range(self, dialog_act_range_href):
    dialog_act_range = dialog_act_range_href.split('#')[-1].split('..')
    dialog_act_id_prefix = '.'.join(dialog_act_range[0].replace('id(', '').replace(')', '').split('.')[0:-1])
    if len(dialog_act_range) < 2:
      dialog_act_range.append(dialog_act_range[0])
    start, end = map(int, [dialog_act_no.replace('id(', '').replace(')', '').split('.')[-1].replace('dialog-act', '') for dialog_act_no in dialog_act_range])
    
    dialog_acts = ''
    start_time = 99999999.99
    end_time = 0.00
    no_of_da = 0
    for i in range(start, end+1):
      if f'{dialog_act_id_prefix}.{i}' not in self.dialog_acts:
        continue
      dialog_act = self.dialog_acts[f'{dialog_act_id_prefix}.{i}']['act']
      start_time = min(self.dialog_acts[f'{dialog_act_id_prefix}.{i}']['start_time'], start_time)
      end_time = max(self.dialog_acts[f'{dialog_act_id_prefix}.{i}']['end_time'], end_time)
      if dialog_act == False:
        continue
      if len(dialog_acts) > 0:
        dialog_acts += ' '
      dialog_acts += dialog_act
      no_of_da += 1
    if dialog_acts == '':
      return {
        'act': False,
        'start_time': start_time,
        'end_time': end_time,
        'count': no_of_da
      }
    return {
        'act': dialog_acts,
        'start_time': start_time,
        'end_time': end_time,
        'count': no_of_da
      }

  """
    Convert Extractive Summary to JSON
  """
  def convert_extractive_summary_to_json(self):
    print(f'Converting Extractive Summary {self.meeting_id} ...')
    self.metadata['ext_summ'] = {
      'types': {}
    }

    ext_summs = []
    ext_summ_file_xml = ET.parse(f'{AMI_DATASET_DIR}/extractive/{meeting_id}.extsumm.xml').getroot()
    self.metadata['ext_sentense_da_count'] = 0

    for ext_summ in ext_summ_file_xml:
      for dialog_act_xml in ext_summ.findall(NITE_CHILD):
        dialog_act_href = dialog_act_xml.get('href')
        dialog_act = self.get_dialog_acts_by_range(dialog_act_href)['act']      
        
        dialog_act_range = dialog_act_href.split('#')[1].split('..')
        if len(dialog_act_range) < 2:
          dialog_act_range.append(dialog_act_range[0])
        start, end = map(int, [dialog_act_no.replace('id(', '').replace(')', '').split('.')[-1].replace('dialog-act', '') for dialog_act_no in dialog_act_range])
        self.metadata['ext_sentense_da_count'] += self.get_dialog_acts_by_range(dialog_act_href)['count'] 

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
        
        if not sub_type:
          continue
        if sub_type in self.metadata['ext_summ']['types']:
          self.metadata['ext_summ']['types'][sub_type] += 1
        else:
          self.metadata['ext_summ']['types'][sub_type] = 1

    self.metadata['ext_sentense_count'] = len(ext_summs)
    with open(f'{self.dest_folder}/extractive_summary.json', 'w') as fp:
      json.dump(ext_summs, fp, sort_keys=True, indent=2)

  """
    Convert Abstractive Summary to JSON
  """
  def convert_abstractive_summary_to_json(self):
    print(f'Converting Abstractive Summary {self.meeting_id} ...')
    if self.is_summ_links_initialized == False:
      self._init_summ_links()
      self.is_summ_links_initialized = True

    abs_summs = {
      'abstract': [],
      'actions': [],
      'decisions': [],
      'problems': []
    }
    
    abs_summ_file_xml = ET.parse(f'{AMI_DATASET_DIR}/abstractive/{meeting_id}.abssumm.xml').getroot()
    ext_count = 0
    
    for abstract in abs_summ_file_xml.find('abstract').findall('sentence'):
      abs_summs['abstract'].append({
        'summary': abstract.text,
        'extract_summ': self.summ_links[abstract.get(NITE_ID)] if abstract.get(NITE_ID) in self.summ_links else []
      })
      ext_count += len(abs_summs['abstract'][-1]['extract_summ'])
    for action in abs_summ_file_xml.find('actions').findall('sentence'):
      abs_summs['actions'].append({
        'summary': action.text,
        'extract_summ': self.summ_links[action.get(NITE_ID)] if action.get(NITE_ID) in self.summ_links else []
      })
      ext_count += len(abs_summs['actions'][-1]['extract_summ'])
    for decision in abs_summ_file_xml.find('decisions').findall('sentence'):
      abs_summs['decisions'].append({
        'summary': decision.text,
        'extract_summ': self.summ_links[decision.get(NITE_ID)] if decision.get(NITE_ID) in self.summ_links else []
      })
      ext_count += len(abs_summs['decisions'][-1]['extract_summ'])
    for problem in abs_summ_file_xml.find('problems').findall('sentence'):
      abs_summs['problems'].append({
        'summary': problem.text,
        'extract_summ': self.summ_links[problem.get(NITE_ID)] if problem.get(NITE_ID) in self.summ_links else []
      })
      ext_count += len(abs_summs['problems'][-1]['extract_summ'])

    self.metadata['abs_summ'] = {
      'ext_summs_count': ext_count,
      'abs_summs_count': len(abs_summs['abstract']) + len(abs_summs['actions']) + len(abs_summs['decisions']) + len(abs_summs['problems']) 
    }
    with open(f'{self.dest_folder}/abstractive_summary.json', 'w') as fp:
      json.dump(abs_summs, fp, sort_keys=True, indent=2)

  """
    Convert Decision Points to JSON
  """
  def convert_decision_points_to_json(self):
    print(f'Converting Decision Points {self.meeting_id} ...')
    global WARNINGS_COUNT

    decision_xml_path = f'{AMI_DATASET_DIR}/decision/manual/{meeting_id}.decision.xml'
    if not os.path.isfile(decision_xml_path):
      print(colored('Decision Points not Exists in DataSet', 'yellow'))
      WARNINGS_COUNT += 1
      return False

    decisions = []
    abs_summ_file_xml = ET.parse(decision_xml_path).getroot()

    for decision in abs_summ_file_xml.findall('decision'):
      decisions.append([])
      decision_points = decision.findall(NITE_CHILD)
      for decision_point in decision_points:
        decision_point_href = decision_point.get('href')
        act, start_time, end_time = itemgetter('act', 'start_time', 'end_time')(self.get_words_by_range(decision_point_href))         
        if not act:
          continue
        decisions[len(decisions) - 1].append({
          'act': act,
          'start_time': start_time,
          'end_time': end_time
        })
    with open(f'{self.dest_folder}/decision_points.json', 'w') as fp:
      json.dump(decisions, fp, sort_keys=True, indent=2)

  """
    Convert Segments to JSON
  """
  def convert_segments_to_json(self):
    print(f'Converting Segments {self.meeting_id} ...')

    segments_xml_roots = self.get_segments_xml_roots()
    segments = []

    for agent, root in segments_xml_roots.items():
      for segment in root.findall('segment'):
        content_words_href = segment.find(NITE_CHILD).get('href')
        content = self.get_words_by_range(content_words_href)
        start_time = float(segment.get('transcriber_start'))
        end_time = float(segment.get('transcriber_end'))
        if content['act']:
          segments.append({
            'speaker_id': agent,
            'start_time': start_time,
            'end_time': end_time,
            'segment': content['act']
          })
          self.segments[segment.get(NITE_ID)] = segments[-1]
          
    self.metadata['segmants'] = len(self.segments)
    with open(f'{self.dest_folder}/words_segmentation.json', 'w') as fp:
      json.dump(segments, fp, sort_keys=True, indent=2)

  """
    Convert Topics Segmentation to JSON
  """
  def convert_topics_to_json(self):
    print(f'Converting Topics {self.meeting_id} ...')
    global WARNINGS_COUNT

    topic_xml_path = f'{AMI_DATASET_DIR}/topics/{meeting_id}.topic.xml'
    if not os.path.isfile(topic_xml_path):
      print(colored('Topics Segmentation not Exists in DataSet', 'yellow'))
      WARNINGS_COUNT += 1
      return False

    topics = []
    topics_file_xml = ET.parse(topic_xml_path).getroot()

    for topic in topics_file_xml.findall('topic'):
      other_description = topic.get('other_description')
      topic_id = topic.find(NITE_POINTER).get('href').replace('default-topics.xml#id(', '').replace(')', '')
      topic_sentenses = topic.findall(NITE_CHILD)
      acts = []
      for topic_sentense in topic_sentenses:
        act = self.get_words_by_range(topic_sentense.get('href'))
        if act['act']:
          acts.append(act)
      topics.append({
        'topic': self.topics[topic_id],
        'other_description': other_description,
        'acts': acts
      })
    
    with open(f'{self.dest_folder}/topic_segmentation.json', 'w') as fp:
      json.dump(topics, fp, sort_keys=True, indent=2)

  """
    Convert Adjacency Pairs to JSON
  """
  def convert_adjacency_pairs_to_json(self):
    print(f'Converting Adjacency Pairs {self.meeting_id} ...')
    self.metadata['ap'] = []

    adjacency_pairs = []
    adjacency_pairs_xml_path = f'{AMI_DATASET_DIR}/dialogueActs/{meeting_id}.adjacency-pairs.xml'
    adjacency_pairs_file_xml = ET.parse(adjacency_pairs_xml_path).getroot()

    for adjacency_pair in adjacency_pairs_file_xml.findall('adjacency-pair'):
      adjacency_pair_type = adjacency_pair.find(".//*[@role='type']").get('href')
      source = adjacency_pair.find(".//*[@role='source']").get('href') if adjacency_pair.find(".//*[@role='source']") is not None else None
      target = adjacency_pair.find(".//*[@role='target']").get('href') if adjacency_pair.find(".//*[@role='target']") is not None else None
      
      if source or target:
        adjacency_pairs.append({
          'type': self.ap_types[adjacency_pair_type.replace('ap-types.xml#id(', '').replace(')', '')],
          'source': self.get_dialog_acts_by_range(source) if source else None,
          'target': self.get_dialog_acts_by_range(target) if target else None
        })

        if not adjacency_pairs[-1]['source'] or not adjacency_pairs[-1]['target']:
          continue
        target_idx = -1
        for idx, val in enumerate(self.metadata['ap']):
          for j in val:
            if j == source:
              target_idx = idx
              break
        
        if target_idx == -1:
          self.metadata['ap'].append([source, target])
        else:
          self.metadata['ap'][target_idx].append(target)
    
    self.metadata['ap_meta'] = {
      'total': 0,
      'far_than_3s': 0,
      'values': []
    }

    for idx1, val1 in enumerate(self.metadata['ap']):
      current_time = self.get_dialog_acts_by_range(val1[0])['end_time']
      for idx2, val2 in enumerate(val1):
        is_in_ext_summ = self.check_dialog_act_in_ext_summ(val2)
        val2 = self.get_dialog_acts_by_range(val2)
        self.metadata['ap'][idx1][idx2] = {
          'start_time': val2['start_time'],
          'end_time': val2['end_time'],
          'act': val2['act'],
          'is_in_ext_summ': is_in_ext_summ
        }
        self.metadata['ap_meta']['total'] += 1
        if current_time + 3 < self.metadata['ap'][idx1][idx2]['start_time']:          
          self.metadata['ap_meta']['values'].append([idx1, current_time])
          self.metadata['ap_meta']['far_than_3s'] += 1
        current_time = self.metadata['ap'][idx1][idx2]['end_time']

    self.metadata['ap_meta']['total_sequences'] = len(self.metadata['ap'])
    with open(f'{self.dest_folder}/adjacency_pairs.json', 'w') as fp:
      json.dump(adjacency_pairs, fp, sort_keys=True, indent=2)

  """
    Convert Argument Structs to JSON
  """
  def convert_argument_structs_to_json(self):
    print(f'Converting Argument Structs {self.meeting_id} ...')

    argument_structs = []
    for file_path in glob.glob(f'{AMI_DATASET_DIR}/argumentation/ae/{self.meeting_id}*'):
      argument_struct_file_xml = ET.parse(file_path).getroot()
      speaker_id = os.path.basename(file_path).split('.')[1]

      for argument_struct in argument_struct_file_xml.findall('ae'):
        ae_type = argument_struct.find(NITE_POINTER).get('href') if argument_struct.find(NITE_POINTER) != None else None
        dialog_act = self.get_words_by_range(argument_struct.find(NITE_CHILD).get('href'))
        
        argument_structs.append({
          'ae_type': None if ae_type == None else self.ae_types[ae_type.replace('ae-types.xml#id(', '').replace(')', '')],
          'speaker_id': speaker_id,
          'act': dialog_act['act'],
          'start_time': dialog_act['start_time'],
          'end_time': dialog_act['end_time']
        })
        self.argument_structs[argument_struct.get(NITE_ID)] = argument_structs[-1]
    
    with open(f'{self.dest_folder}/argument_structs.json', 'w') as fp:
      json.dump(argument_structs, fp, sort_keys=True, indent=2)

  """
    Convert Argumentation Rels to JSON
  """
  def convert_argumentation_rels_to_json(self):
    print(f'Converting Argumentation Rels {self.meeting_id} ...')
    global WARNINGS_COUNT

    argumentation_rels = []
    argumentation_rels_xml_path = f'{AMI_DATASET_DIR}/argumentation/ar/{meeting_id}.argumentationrels.xml'
    if not os.path.isfile(argumentation_rels_xml_path):
      print(colored('Argumentation Rels not Exists in DataSet', 'yellow'))
      WARNINGS_COUNT += 1
      return False
    argumentation_rels_file_xml = ET.parse(argumentation_rels_xml_path).getroot()

    for argumentation_rel in argumentation_rels_file_xml.findall('ar'):
      ar_type = argumentation_rel.find(".//*[@role='type']").get('href') if argumentation_rel.find(".//*[@role='type']") != None else None
      source = argumentation_rel.find(".//*[@role='source']").get('href').split('#')[1].replace('id(', '').replace(')', '') if argumentation_rel.find(".//*[@role='source']") is not None else None
      target = argumentation_rel.find(".//*[@role='target']").get('href').split('#')[1].replace('id(', '').replace(')', '') if argumentation_rel.find(".//*[@role='target']") is not None else None
      

      argumentation_rels.append({
        'ar_type': self.ar_types[ar_type.replace('ar-types.xml#id(', '').replace(')', '')] if ar_type != None else None,
        'source': self.argument_structs[source],
        'target': self.argument_structs[target]
      })
    
    with open(f'{self.dest_folder}/argumentation_relationships.json', 'w') as fp:
      json.dump(argumentation_rels, fp, sort_keys=True, indent=2)

  """
    Convert Argument Discussions to JSON
  """
  def convert_argument_discussions_to_json(self):
    print(f'Converting Argument Discussions {self.meeting_id} ...')
    global WARNINGS_COUNT

    argument_discussions = []
    argument_discussions_xml_path = f'{AMI_DATASET_DIR}/argumentation/dis/{meeting_id}.discussions.xml'
    if not os.path.isfile(argument_discussions_xml_path):
      print(colored('Argument Discussions not Exists in DataSet', 'yellow'))
      WARNINGS_COUNT += 1
      return False
    argument_discussions_file_xml = ET.parse(argument_discussions_xml_path).getroot()

    for argument_discussion in argument_discussions_file_xml.findall('discussion-fragment'):
      argument_discussion_type = argument_discussion.get('name')
      argument_discussion_acts = []
      for argument_discussion_act in argument_discussion.findall(NITE_CHILD):
        argument_discussion_act_href = argument_discussion_act.get('href').split('#')[1].replace('id(', '').replace(')', '')    
        argument_discussion_acts.append(self.get_segments_by_range(argument_discussion_act_href))

      argument_discussions.append({
        'type': argument_discussion_type.split(' - ')[-1],
        'segments': argument_discussion_acts
      })
    
    with open(f'{self.dest_folder}/argument_discussions.json', 'w') as fp:
      json.dump(argument_discussions, fp, sort_keys=True, indent=2)

  def metadata_to_json(self):
    with open(f'{self.dest_folder}/metadata.json', 'w') as fp:
      json.dump(self.metadata, fp, sort_keys=True, indent=2)

# Main
all_meeting_ids = GetAllMeetingIDs()
for meeting_id in all_meeting_ids:
  meeting = Meeting(meeting_id)
  meeting.print_meeting_metadata()
  # meeting.copy_audio_dataset()
  meeting.convert_transcript_to_json()
  meeting.convert_dialog_acts_to_json()
  meeting.convert_adjacency_pairs_to_json()
  meeting.convert_segments_to_json()
  meeting.convert_decision_points_to_json()
  meeting.convert_topics_to_json()
  meeting.convert_extractive_summary_to_json()
  meeting.convert_abstractive_summary_to_json()
  meeting.convert_argument_structs_to_json()
  meeting.convert_argumentation_rels_to_json()  
  meeting.convert_argument_discussions_to_json()
  meeting.metadata_to_json()

print('--------------------------------')
all_metadata = []
for meeting_id in all_meeting_ids:
  with open(f'dataset/{meeting_id}/metadata.json') as outfile:
    metadata = json.load(outfile)
    metadata['ext_sentense_da_count_per'] = int((metadata['ext_sentense_da_count'] / metadata['abs_summ']['ext_summs_count']) * 100)
    all_metadata.append({
      'meeting': meeting_id,
      'metadata': metadata
    })
    print(metadata)
with open(f'dataset/all_metadata.json', 'w') as fp:
      json.dump(all_metadata, fp, sort_keys=True, indent=2)

if ERROR_COUNT == 0:
  print(colored(f"\nExecuted Success with {ERROR_COUNT} Errors & {WARNINGS_COUNT} Warnings", 'green'))
else:
  print(colored(f"\nExecuted Failed with {ERROR_COUNT} Errors & {WARNINGS_COUNT} Warnings", 'red'))
