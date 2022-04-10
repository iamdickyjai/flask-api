from speechbrain.dataio.dataio import read_audio
from speechbrain.pretrained import VAD
from speechbrain.utils.data_utils import split_path
from speechbrain.pretrained.fetching import fetch
from speechbrain.pretrained import EncoderClassifier
import speechbrain.processing.diarization as diar
import torch
import logging

"""
All timestamp are formatted in 2 d.p.
"""

# Pretrained model used
v = VAD.from_hparams(
    source="speechbrain/vad-crdnn-libriparty", savedir="./pretrained_models/VAD"
)
classifier = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="./pretrained_models/EMB",
)

# logging.basicConfig(filename="diar.log",
#                     filemode="a",
#                     format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
#                     datefmt='%H:%M:%S',
#                     level=logging.INFO)


def diarization(path):
    try:
        logging.info("Start diarization")

        # Speaker Segmentation & Speaker Embedding
        [embeddings, timestamp] = segNemb(path)

        # Speaker Clustering
        lol = spec_clust(embeddings=embeddings, timestamp=timestamp)

        logging.info("Diarization finished")
        return lol
    except Exception:
        return Exception


# Return a list of arrays e.g. [[0.00, 1.23], [1.29, 3.23]]
def pre_processing(path):
    logging.info("Start Preprocessing")

    boundaries = get_speech_segments(path, v)
    boundaries = boundaries.tolist()
    boundaries_round = round_down_boundaries(boundaries, 2)

    logging.info("Preprocessing end")
    return boundaries_round


# Return [list_emb, list_timestamp]
def segNemb(path, sampling_rate=16000, vad=False):
    """
    path            : string, Point to the location of the audio file.
                      Should be a virtual directory.
    sampling_rate   : integer
    vad             : Boolean, decide if VAD should be used
    """
    wav = read_audio(path)
    length = len(wav)
    segment_len = 1.5

    activities = (
        pre_processing(str(path))
        if vad
        else [[0, round(float(length / sampling_rate), 2)]]
    )

    # Store the embeddings and timestamp for each segment
    embeddings = []
    timestamp = []

    logging.info("Start Speaker embedding")
    for act in activities:
        # Get the starting and ending time of current section
        start_time = act[0]
        end_time = act[1]

        # Initialize the parameter to be used
        seg_start_time = start_time
        seg_end_time = seg_start_time + segment_len

        while seg_end_time < end_time:
            # Set up the end time for this segment
            seg_end_time = (
                seg_start_time + segment_len
                if seg_start_time + segment_len <= end_time
                else end_time
            )

            # Ignore segment if it is too tiny
            seg_duration = seg_end_time - seg_start_time
            if seg_duration >= 0.05:
                # Label the time activities of this embedding
                timestamp.append(((seg_start_time, seg_end_time)))

                # Setting the frames for actual embedding process
                start_frame = int(seg_start_time * sampling_rate)
                end_frame = int(seg_end_time * sampling_rate)
                segment = wav[start_frame:end_frame]

                # Perform Speaker Embedding
                e = classifier.encode_batch(segment)
                embeddings.append(e[0, 0].numpy())

            # Start point move to next semgent
            next_start = seg_start_time + segment_len / 2
            seg_start_time = round(float(next_start), 2)

    logging.info("Speaker embedding finished")
    return [embeddings, timestamp]


# Return [["audio", sseg_start, sseg_end, spkr_id]]
# Example: [["audio", 0.00, 0.75, 1], ["audio", 0.75, 1.5, 3]...]
def spec_clust(embeddings, timestamp):
    """
    embeddings  : A list of embeddings
    timestamp   : A list of timestamp, each contain start time and end time
    """

    logging.info("Start Clustering")

    # Define the clustering
    clust_obj = diar.Spec_Clust_unorm(min_num_spkrs=2, max_num_spkrs=10)

    # Pefrom the clustering and receive the label
    clust_obj.do_spec_clust(embeddings, None, 0.2)
    labels = clust_obj.labels_

    subseg_ids = timestamp
    lol = []

    for i in range(labels.shape[0]):
        sseg_start = float(subseg_ids[i][0])
        sseg_end = float(subseg_ids[i][1])
        spkr_id = labels[i]

        lol.append(["audio", sseg_start, sseg_end, spkr_id])

    lol.sort(key=lambda x: float(x[1]))
    lol = diar.merge_ssegs_same_speaker(lol)
    lol = diar.distribute_overlap(lol)

    # Hard code to convert array into correct format for jsonify
    new_lol = []
    for ele in lol:
        new_lol.append([round(ele[1], 2), round(ele[2], 2), int(ele[3])])

    logging.info("Clustering finished")
    return new_lol


# From speechBrain.pretrained.VAD
# Modify to disable save to local file, other remain the same
def get_speech_segments(path, VAD):
    source, fl = split_path(path)
    audio_file = fetch(fl, source=source, savedir="/tmp")

    # Computing speech vs non speech probabilities
    prob_chunks = VAD.get_speech_prob_file(audio_file)

    # Apply a threshold to get candidate speech segments
    prob_th = VAD.apply_threshold(prob_chunks).float()

    # Comupute the boundaries of the speech segments
    boundaries = VAD.get_boundaries(prob_th, output_value="seconds")

    # Merge short segments
    boundaries = VAD.merge_close_segments(boundaries)

    # Remove short segments
    boundaries = VAD.remove_short_segments(boundaries)

    return boundaries


def round_down_boundaries(boundaries, dp):
    round_boundaires = []
    for boundary in boundaries:
        tmp_boundary = []
        start = boundary[0]
        end = boundary[1]

        start_round = round(start, dp)
        end_round = round(end, dp)

        tmp_boundary.append(start_round)
        tmp_boundary.append(end_round)

        round_boundaires.append(tmp_boundary)

    return round_boundaires
