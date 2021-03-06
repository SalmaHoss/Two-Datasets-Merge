# -*- coding: utf-8 -*-
import os
import glob
import argparse
import numpy as np
import random
import soundfile as sf
from enum import Enum
from tqdm import tqdm
from scipy.io import wavfile


class EncodingType(Enum):
    def __new__(cls, *args, **kwds):
        value = len(cls.__members__) + 4
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, dtype, description, subtype, maximum, minimum):
        self.dtype = dtype
        self.description = description
        self.subtype = subtype
        self.maximum = maximum
        self.minimum = minimum

    # Available subtypes
    # See. https://pysoundfile.readthedocs.io/en/latest/#soundfile.available_subtypes
    INT16 = (
        "int16",
        "Signed 16 bit PCM",
        "PCM_16",
        np.iinfo(np.int16).max,
        np.iinfo(np.int16).min,
    )
    INT32 = (
        "int32",
        "Signed 32 bit PCM",
        "PCM_32",
        np.iinfo(np.int32).max,
        np.iinfo(np.int32).min,
    )
    FLOAT32 = ("float32", "32 bit float", "FLOAT", 1, -1)
    FLOAT64 = ("float64", "64 bit float", "DOUBLE", 1, -1)


def get_args():
    parser = argparse.ArgumentParser()  # place of the file to be run
    parser.add_argument("--clean_folder", type=str, required=True)  # clean file => clean folder
    parser.add_argument("--noise_folder", type=str, required=True)  # noise file => noise folder
    parser.add_argument("--output_mixed_file", type=str, default="", required=True)  # mixed file
    parser.add_argument("--output_clean_file", type=str, default="")
    parser.add_argument("--output_noise_file", type=str, default="")
    parser.add_argument("--snr", type=float, default="", required=True)  # value
    args = parser.parse_args()
    return args
    ##FROM ToyAdmos => Read From given folder##


def wavread(fn):
    fs, data = wavfile.read(fn)
    data = (data.astype(np.float32) / 2 ** (15))
    return data, fs

    ##Call it with clean folder given and noise##


def wav_read_all(wav_dir):
    path, dirs, files = next(os.walk(wav_dir))  # get them
    file_count = len(files)  # number of files in dir
    # print("Here " + wav_dir,file_count)
    wav_file_set = []
    Num_wav = 0
    # for i in range(file_count):
    wav_file_set = os.listdir(wav_dir)  # put them in the set
    Num_wav = len(wav_file_set)
    # print("Final "+wav_dir,Num_wav)
    # till here it isnot the write file format
    S_all = []
    fn_all = []
    signals = []  # must be 1 element

    for item in wav_file_set:
        fn = str(item)
        print(fn)
        data, org_fs = wavread(wav_dir + '/' + fn)
        signals.append(data)
        fn_all.append(wav_dir + '/' + fn)
    signal = signals[0]
    # if(org_fs != target_fs):
    #        signal = librosa.core.resample( signal, org_fs, target_fs )
    # fn = fn[len(wav_dir):].replace( ch_num[-1], 'chAll' )
    S_all.append(signal)
    # return Num_wav,wav_file_set
    return Num_wav, S_all, fn_all


#######################################################


def cal_adjusted_rms(clean_rms, snr):
    a = float(snr) / 20
    noise_rms = clean_rms / (10 ** a)
    return noise_rms


def cal_rms(amp):
    return np.sqrt(np.mean(np.square(amp), axis=-1))


def save_waveform(output_path, amp, samplerate, subtype):
    sf.write(output_path, amp, samplerate, format="wav", subtype=subtype)


if __name__ == "__main__":
    args = get_args()
    clean_folder = args.clean_folder
    noise_folder = args.noise_folder

    Num_clean_files, signal_clean_files, clean_files = wav_read_all(clean_folder)
    Num_noise_files, signal_noise_files, noise_files = wav_read_all(noise_folder)
    print("Number of files in clean ", Num_clean_files)
    iter = min(Num_noise_files, Num_clean_files)  # not good way but for trying
for i in range(iter):
    metadata = sf.info(clean_files[i])
    for item in EncodingType:
        if item.description == metadata.subtype_info:
            encoding_type = item

    clean_amp, clean_samplerate = sf.read(clean_files[i], dtype=encoding_type.dtype)
    noise_amp, noise_samplerate = sf.read(noise_files[i], dtype=encoding_type.dtype)

    clean_rms = cal_rms(clean_amp)

    start = random.randint(0, len(noise_amp) - len(clean_amp))
    divided_noise_amp = noise_amp[start: start + len(clean_amp)]
    noise_rms = cal_rms(divided_noise_amp)

    snr = args.snr
    adjusted_noise_rms = cal_adjusted_rms(clean_rms, snr)

    adjusted_noise_amp = divided_noise_amp * (adjusted_noise_rms / noise_rms)
    mixed_amp = clean_amp + adjusted_noise_amp

    # Avoid clipping noise
    max_limit = encoding_type.maximum
    min_limit = encoding_type.minimum
    if mixed_amp.max(axis=0) > max_limit or mixed_amp.min(axis=0) < min_limit:
        if mixed_amp.max(axis=0) >= abs(mixed_amp.min(axis=0)):
            reduction_rate = max_limit / mixed_amp.max(axis=0)
        else:
            reduction_rate = min_limit / mixed_amp.min(axis=0)
        mixed_amp = mixed_amp * (reduction_rate)
        clean_amp = clean_amp * (reduction_rate)
    output_file_name = args.output_mixed_file + '_' + str(i)
    print("Name of the two mixed files ", clean_files[i], noise_files[i])
    save_waveform(
        output_file_name, mixed_amp, clean_samplerate, encoding_type.subtype
    )
