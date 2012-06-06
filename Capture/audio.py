from os.path import exists
from array import array
from struct import unpack, pack
from time import sleep

import pyaudio
import wave

def normalize(sound_data):
	numbits = 15 # normalize to 16-bit sounds
	new_max_amplitude = float((2**(numbits-1)) - 1)
	current_max_amplitude = float(max( abs(min(sound_data)), abs(max(sound_data)) ))
	return [int(float(sample) / current_max_amplitude * new_max_amplitude) for sample in sound_data]

def normalize_dev(L):
	"Average the volume out"
	max_volume = 16384
	times = float(max_volume)/max(abs(i) for i in L)

	LRtn = array('h')
	for i in L:
		LRtn.append(int(i*times))
	return LRtn

def trim(L):
	"Trim the blank spots at the start and end"
	threshold = 500
	def _trim(L):
		snd_started = False
		LRtn = array('h')

		for i in L:
			if not snd_started and abs(i)>threshold:
				snd_started = True
				LRtn.append(i)

			elif snd_started:
				LRtn.append(i)
		return LRtn

	# Trim to the left
	L = _trim(L)

	# Trim to the right
	L.reverse()
	L = _trim(L)
	L.reverse()
	return L

def add_silence(L, seconds):
	"Add silence to the start and end of `L` of length `seconds` (float)"
	rate = 44100
	LRtn = array('h', [0 for i in xrange(int(seconds*rate))])
	LRtn.extend(L)
	LRtn.extend([0 for i in xrange(int(seconds*rate))])
	return LRtn


# strangely the record_audio function lags considerably
# when it is not within the main.py file (perhaps this is a PyAudio problem?) 
def record_audio(pipe, verbose=False):
	"""record_audio:
		- Initialize a global array to hold audio 
		- if record and not running initiaize PyAudio Stream 
		- if recording and running, add to data list
		- if not recording and not running, clean up data and save to wav
	"""
	chunk_size = 1536
	g_LRtn = array('h')

	while True:
		r_audio, running, audio_out = pipe.recv() 

		if r_audio and not running:
			p = pyaudio.PyAudio()
			if verbose: print "Initialized PyAudio stream for recording"
			stream = p.open(input_device_index=0, format=pyaudio.paInt16, 
						channels=1, rate=44100, 
						input=True, output=True,
						frames_per_buffer=chunk_size, 
						start = False)
		if r_audio and running:
			# print "recording audio..."
			#sleep(0.01)
			try:
				stream.start_stream()
				data = stream.read(chunk_size)
				L = unpack('<' + ('h'*(len(data)/2)), data) # little endian, signed short
				L = array('h', L)
				g_LRtn.extend(L)
				if verbose: print "len(g_LRtn): %s" %(len(g_LRtn))
			except IOError,e:
				if e[1] == pyaudio.paInputOverflowed: 
					print e
					print "Audio Buffer overflow "
					data = '\x00'*pyaudio.paInt16*chunk_size*1
				else:
					raise
		if not r_audio and not running:
			if verbose: print "Stopped recording...Saving File"
			sample_width = p.get_sample_size(pyaudio.paInt16)
			stream.stop_stream()
			stream.close()
			p.terminate()

			if verbose: print "len(g_LRtn): ", len(g_LRtn)
			g_LRtn = normalize(g_LRtn)
			# g_LRtn = trim(g_LRtn)
			# g_LRtn = add_silence(g_LRtn, 0.5)

			data = pack('<' + ('h'*len(g_LRtn)), *g_LRtn)

			wf = wave.open(audio_out, 'wb')
			wf.setnchannels(1)
			wf.setsampwidth(sample_width)
			wf.setframerate(44100)
			wf.writeframes(data)
			wf.close()
			if verbose: print "Saved audio to: %s" %audio_out
			# clear global array when done recording
			g_LRtn = array('h')

