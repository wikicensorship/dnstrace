#!/usr/bin/env python3

import os
import json
import time
import platform
from urllib.request import Request, urlopen
from multiprocessing import Process, Value, RawArray 
import ctypes 
from threading import Thread 


OS_NAME = platform.system()


def get_meta_json():
    meta_url = 'https://speed.cloudflare.com/meta'
    # TODO(xhdix): change versioning
    httprequest = Request(
        meta_url, headers={'user-agent': 'TraceVis/0.7.0 (WikiCensorship)'})
    try:
        with urlopen(httprequest, timeout=9) as response:
            if response.status == 200:
                meta_json = json.load(response)
                return meta_json
            else:
                return None
    except Exception as e:
        print(f"Notice!\n{e!s}")
        return None


def drop_privileges():
    if os.name == 'posix':
        if os.geteuid() == 0:
            uid = os.geteuid()
            gid = os.getegid()
            os.setegid(65534)
            os.seteuid(65534)
            return uid, gid
    return None, None

def gain_privileges(uid, gid):
    if uid is not None and gid is not None:
        os.setegid(gid)
        os.seteuid(uid)


def posix_run_geolocate():
    def get_meta(no_internet, public_ip, network_asn, network_name, country_code, city):

        no_internet.value = True
        public_ip.value = '127.1.2.7'  # we should know that what we are going to clean
        network_asn.value = 'AS0'
        network_name.value = ''
        country_code.value = ''
        city.value = ''

        print("· - · · · detecting IP, ASN, country, etc (Posix) · - · · · ")
        user_meta = get_meta_json()
        if user_meta is not None :
            no_internet.value = False
            if 'clientIp' in user_meta.keys():
                public_ip.value = user_meta['clientIp']
                print("· · · - · " + public_ip.value)
                print('. - . - . we use public IP to know what to remove from data!')
            if 'asn' in user_meta.keys():
                network_asn.value = ("AS" + str(user_meta['asn']))
                print("· · · - · " + network_asn.value)
            if 'asOrganization' in user_meta.keys():
                network_name.value = user_meta['asOrganization']
                print("· · · - · " + network_name.value)
            if 'country' in user_meta.keys():
                country_code.value = user_meta['country']
                print("· · · - · " + country_code.value)
            if 'city' in user_meta.keys():
                city.value = user_meta['city']
                print("· · · - · " + city.value)


    user_meta_info_timeout = 10   # Seconds
    no_internet = True 
    public_ip = ""
    network_asn = ""
    network_name = ""
    country_code = ""
    city = ""

    user_meta_info_start_time = 0

    no_internet = Value(ctypes.c_bool, True)
    public_ip = RawArray(ctypes.c_wchar, 40)
    network_asn = RawArray(ctypes.c_wchar, 100)
    network_name = RawArray(ctypes.c_wchar, 100)
    country_code = RawArray(ctypes.c_wchar, 100)
    city = RawArray(ctypes.c_wchar, 100)
    
    uid, gid = drop_privileges()
    p = Process(target=get_meta, daemon=True, args=(no_internet, public_ip, network_asn, network_name, country_code, city))
    p.start()
    user_meta_info_start_time = time.time()

    while time.time() - user_meta_info_start_time < user_meta_info_timeout and no_internet: 
        time.sleep(1)
    
    gain_privileges(uid, gid)

    return no_internet.value, public_ip.value, network_asn.value, network_name.value, country_code.value, city.value



def windows_run_geolocate():
    def get_meta():
        nonlocal no_internet, public_ip, network_asn, network_name, country_code, city, is_canceled

        no_internet = True
        public_ip = '127.1.2.7'  # we should know that what we are going to clean
        network_asn = 'AS0'
        network_name = ''
        country_code = ''
        city = ''


        print("· - · · · detecting IP, ASN, country, etc (Windows) · - · · · ")
        user_meta = get_meta_json()
        if is_canceled:
            return
        if user_meta is not None :
            no_internet = False
            if 'clientIp' in user_meta.keys():
                public_ip = user_meta['clientIp']
                print("· · · - · " + public_ip)
                print('. - . - . we use public IP to know what to remove from data!')
            if 'asn' in user_meta.keys():
                network_asn = ("AS" + str(user_meta['asn']))
                print("· · · - · " + network_asn)
            if 'asOrganization' in user_meta.keys():
                network_name = user_meta['asOrganization']
                print("· · · - · " + network_name)
            if 'country' in user_meta.keys():
                country_code = user_meta['country']
                print("· · · - · " + country_code)
            if 'city' in user_meta.keys():
                city = user_meta['city']
                print("· · · - · " + city)


    user_meta_info_timeout = 10   # Seconds
    no_internet = True 
    public_ip = ""
    network_asn = ""
    network_name = ""
    country_code = ""
    city = ""
    is_canceled = False

    user_meta_info_start_time = 0

    p = Thread(target=get_meta, daemon=True)
    p.start()
    user_meta_info_start_time = time.time()
    while time.time() - user_meta_info_start_time < user_meta_info_timeout and no_internet:
        time.sleep(1)
    if no_internet:
        is_canceled = True
        
    return no_internet, public_ip, network_asn, network_name, country_code, city



def run_geolocate():
    # threat windows and other posix systems differently
    # windows get suspious when we spawn an independant Process 
    # so we need to use thread for that
    # in other posix systems we need dropping privilege and as 
    # this is not possible in python threads we stick to process for those systems
    if os.name == "posix":
        return posix_run_geolocate()
    return windows_run_geolocate()
