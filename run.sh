#!/bin/bash

export PYTHONPATH=$PWD

uvicorn app:app --reload
