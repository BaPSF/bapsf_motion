# -*- coding: utf-8 -*-
r"""
find_ip_addr(search_str, ip_range='') -> ()

Returns a list of ip addresses associated with a particular adapter manufacturer
See example below for usage

Uses the program nmap to accomplish the results. This should be installed on the system,
but here we use hardwired paths:
	Linux:   /usr/bin/nmap
	Windows: looks in C:\Program Files (x86) for an nmap directory

Created on Sep 1(?)

@author: Patrick
"""
import sys
if sys.version_info[0] < 3: raise RuntimeError('This script should be run under Python 3')

import os
import socket
import subprocess

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# throws this exception if search fails

class find_ip_addr_error(Exception):
	""" our local error exception; has no behavior of its own"""
	pass

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def my_ip_addr() -> str:
	""" worker for below: used to determine the 24 bit subnet address of our local lan"""
	if sys.platform == 'linux':
		test_ip_addr = '8.8.8.8'
		r = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect((test_ip_addr, 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
		if len(r) == 0:
			raise find_ip_addr_error('*** my_ip_addr(): This computer does not seem to have an IP address')
		return r
		# this opaque technique is from http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
		# I'm not sure it works, since it returns the same result when the RJ45 connection is unplugged and there is no internet connection, AND also when the wifi subsequently connects with a different IP address
		# Also, on my subnet at home, it (cleverly) returns the internet facing IP, rather than e.g. '192.169.1.5'; unfortunately the latter is what we need in this instance
	else:
		# on the other hand, the following works on windows but not on Linux:
		ip_addrs = socket.gethostbyname_ex(socket.gethostname())[2]
#??? Behavior changed again? 3/27/2017 had to remove this because  len(ip_addrs) is 1 now
#???		if len(ip_addrs) < 2:
#???			raise find_ip_addr_error('*** my_ip_addr(): This computer does not seem to have an IP address')
		return ip_addrs[-1]              # = current ipv4 address, e.g. '192.168.1.100'
		# was return ip_addrs[1]                # = current ipv4 address, e.g. '192.168.1.100'

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# main routine

def find_ip_addr(search_str, ip_range='') -> ():
	""" uses nmap to find the ip address associated with search_str. e.g. "Raspberry PI" or "Avalue Technology" """
	if len(ip_range) == 0:
		ip_addr = my_ip_addr()
		if len(ip_addr) == 0:
			raise find_ip_addr_error('*** find_ip_addr(): local ip address not determined')
		ip_range = ip_addr[0:ip_addr.rfind('.')] + '.*'   # change last byte to '*'

	if sys.platform == 'linux':
		nmap_path = '/usr/bin/nmap'
	else:
		# assume windows, and that nmap is installed in a directory like "C:\Program Files (x86)\nmap-7.12"
		WPF = os.getenv("programfiles(x86)")   # I guess fix this if not 64 bit windows
		dl = [d for d in os.listdir(WPF) if d.lower().find('nmap') == 0]
		if len(dl) == 0:
			WPF = os.getenv("programfiles")
		dl = [d for d in os.listdir(WPF) if d.lower().find('nmap') == 0]
		if len(dl) == 0:
			print("*** find_ip_addr(): cannot find nmap.exe (see https://nmap.org)")   # note: this is windows we are failing on
			raise(find_ip_addr_error("cannot find nmap.exe (see https://nmap.org)"))
		nmap_path = os.path.join(WPF, dl[-1], 'nmap.exe')        # use last occurrence, which is presumably the highest version

	args = [nmap_path, "-n", "-sn", ip_range]        # e.g.   nmap -n -sn 192.168.1.*

	if sys.platform == 'linux':
		args = ['sudo'] + args  # needs to be root to get MAC and vendor info, for some reason

	print('Running nmap to search '+ip_range+' for "'+search_str+'"', flush=True, end='')

	# this works, but then complains about nonsense (Python 3.5 on Windows):
	#      t = os.spawnv(os.P_WAIT, args[0], args)
	# instead, do this (and capture the output):

	nmap_results = ''
	if sys.hexversion < 0x03050000:
		# ugh bumped into this because Pi ships with Python 3.4, which does not have subprocess.run()
		sco = subprocess.check_output(args)
		# will raise exception CalledProcessError if return code != 0
		nmap_results = str(sco)
	else:
		cpo = subprocess.run(args, stdout=subprocess.PIPE)
		if cpo.returncode != 0:
			raise find_ip_addr_error('Failed to run "'+args[0]+'"')
		nmap_results = str(cpo.stdout)

	""" nmap output is a series of 3-line descriptions of the form
	   ...
	Nmap scan report for 192.168.1.5
	Host is up (0.080s latency).
	MAC Address: B8:27:EB:A5:B1:91 (Raspberry Pi Foundation)
	   ...
	"""
	addrs = ()
	while len(nmap_results) > 0:
		i = nmap_results.find(search_str)    # find our target
		if i < 0:
			break
		k = i + len(search_str)
		i = nmap_results[0:i].rfind("report for ")   # backwards search starting at our target
		if i < 0:
			raise find_ip_addr_error('nmap results are funny: found "'+search_str+'" but could not find the text "report for"')
			return addrs
		i += len("report for ")
		j = nmap_results[i:].find("\\r\\n")
		if j < 0:
			j = len(nmap_results[i:])
		addrs += (nmap_results[i:i+j],)
		nmap_results = nmap_results[k:]   # repeat, starting after the found text

	if len(addrs) == 0:
		print(' -> not found')
		raise find_ip_addr_error('nmap did not find "'+search_str+'"')
	else:
		print(' ->',addrs)
	return addrs

#========================================================================================
# example:

if __name__ == '__main__':
	# if we are running this file as a standalone program:

	import tkinter
	import tkinter.messagebox
	try:
		pi_addrs = find_ip_addr("Raspberry Pi")
	except find_ip_addr_error:
		pi_addrs = ()

	try:
		lecroy_addrs = find_ip_addr("Avalue Technology")  # LeCroy
	except find_ip_addr_error:
		lecroy_addrs = ()

	if len(lecroy_addrs) == 0:
		try:
			lecroy_addrs = find_ip_addr("BCM Computers")  # LeCroy
		except find_ip_addr_error:
			lecroy_addrs = ()

	if len(lecroy_addrs) == 0:
		try:
			lecroy_addrs = find_ip_addr("iPOX Technology")  # LeCroy
		except find_ip_addr_error:
			lecroy_addrs = ()

	w = tkinter.Tk()  # create tk window, so that we can eliminate it after the messagebox is finished
	#w.iconify()       # get it off the screen, at least as much as possible
	w.withdraw()      # get it off the screen
	tkinter.messagebox.showinfo(title="find_ip_addr.py",
	                            message='Raspberry Pi ip address:\r\n'+str(list(pi_addrs)) + '\r\n' +
	                                    'LeCroy ip address:\r\n'      +str(list(lecroy_addrs)))
	w.destroy()     # dump the tk window

	print("pi: ", list(pi_addrs))
	print("LeCroy:", list(lecroy_addrs))
	print("done")
