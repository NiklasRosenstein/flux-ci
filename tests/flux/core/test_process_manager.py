
from flux.core.process_manager import ProcessConfiguration, ProcessEventSink, ProcessManager
import threading

def test_process_manager():
  lock = threading.Lock()
  finished_processes = []
  class EventSink(ProcessEventSink):
    def process_finished(self, process_id, process):
      with lock:
        finished_processes.append(process_id)

  manager = ProcessManager(EventSink(), default_poll_interval=1)

  assert not manager.started
  manager.start()
  assert manager.started

  manager.start_process('p1', ProcessConfiguration(['sleep', '1']))
  manager.start_process('p2', ProcessConfiguration(['sleep', '4']))
  manager.start_process('p3', ProcessConfiguration(['sleep', '2']))

  manager.stop()
  assert finished_processes == ['p1', 'p3', 'p2']
