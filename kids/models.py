# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.validators import RegexValidator

import uuid

# Create your models here.
class User(models.Model):
	alphanumeric = RegexValidator(r'^[0-9a-zA-Z]+$', 'Only alphanumeric characters are allowed.')
	alphabets=RegexValidator(r'^[a-zA-Z]{3}$','Only alphabets')
	email = models.EmailField(default=None)
	parentmail = models.EmailField(default=None)
	name = models.CharField(max_length=120,validators=[alphabets])
	username = models.CharField(max_length=120,unique=True,validators=[alphanumeric])   
	password = models.CharField(max_length=40)
	created_on = models.DateTimeField(auto_now_add=True)
	updated_on = models.DateTimeField(auto_now=True)

	def __unicode__(self):

		return self.username


class SessionToken(models.Model):
	user = models.ForeignKey(User)
	session_token = models.CharField(max_length=255)
	last_request_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)
	is_valid = models.BooleanField(default=True)

	def create_token(self):
		self.session_token = uuid.uuid4()


class PostModel(models.Model):
	user = models.ForeignKey(User)
	image = models.FileField(upload_to='user_images')
	image_url = models.CharField(max_length=255)
	caption = models.CharField(max_length=240)
	created_on = models.DateTimeField(auto_now_add=True)
	updated_on = models.DateTimeField(auto_now=True)
	has_liked = False
	@property
	def number_of_likes(self):
		return len(LikeModel.objects.all().filter(post=self))
	@property
	def comments(self):
		return CommentModel.objects.all().filter(post=self).order_by('-created_on')



	def __unicode__(self):
		return self.user.username

class LikeModel(models.Model):
	user=models.ForeignKey(User)
	post=models.ForeignKey(PostModel)
	created_on = models.DateTimeField(auto_now_add=True)
	updated_on = models.DateTimeField(auto_now=True)
	has_liked=models.BooleanField(default=False)

class CommentModel(models.Model):
	user = models.ForeignKey(User)
	post = models.ForeignKey(PostModel)
	comment_text = models.CharField(max_length=200)
	created_on = models.DateTimeField(auto_now_add=True)
	updated_on = models.DateTimeField(auto_now=True)

