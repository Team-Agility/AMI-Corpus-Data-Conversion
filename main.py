from playsound import playsound
import time

class Audio:
  def __init__(self, meeting_id):
    self.meeting_id = meeting_id

  def path(self):
    return f'amicorpus/{self.meeting_id}/audio/{self.meeting_id}.Mix-Headset.wav'

  def play(self):
    playsound(self.path(), False)

  def get_transcript(self):
    timer = time.time()
    time.sleep(5)
    print(time.time() - timer)

meeting1 = Audio('ES2002a')
meeting1.play()
while True:
  meeting1.get_transcript()