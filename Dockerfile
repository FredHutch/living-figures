FROM quay.io/hdc-workflows/widgets:v2.7.7
LABEL author="sminot@fredhutch.org"

ADD ./ /usr/local/living_figures
WORKDIR /usr/local/living_figures
RUN pip3 install ./
