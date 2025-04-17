# after installing demucs...
COPY dummy.wav /tmp/dummy.wav
RUN demucs -n htdemucs_6s /tmp/dummy.wav --segment 1 --two-stems guitar --no-split --out /tmp/model_download && rm -rf /tmp/model_download

