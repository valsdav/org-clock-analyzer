#!/bin/sh -e

export FLASK_ENV=development
export FLASK_APP=server

source myenv/bin/activate
python -m flask run &

cd org-clock-plot
npm run dev 
