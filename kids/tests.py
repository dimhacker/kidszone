# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from clarifai.rest import ClarifaiApp
clarifai_key="ef38d4e4c7294e55919e9a907328a3ed"

app = ClarifaiApp(api_key=clarifai_key)

model = app.models.get('general-v1.3')


response=model.predict(url='http://i.huffpost.com/gen/1374232/images/o-NUDITY-facebook.jpg')
print response

# Create your tests here.
