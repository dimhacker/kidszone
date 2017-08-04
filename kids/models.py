# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.validators import RegexValidator

import uuid

# Create your models here.
class User(models.Model):
	alphabets = RegexValidator(r'[a-zA-Z]{3,40}$')
	alphanumeric=RegexValidator(r'^[a-zA-Z0-9_-]{3,40}$')
	minlength_password=RegexValidator(r'.{4,40}')
	email = models.EmailField(default=None)
	parentmail = models.EmailField(default=None)
	name = models.CharField(max_length=40,validators=[alphabets])
	username = models.CharField(max_length=40,validators=[alphanumeric])
	password = models.CharField(max_length=40,validators=[minlength_password])
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

class CommentModel(models.Model):
    user = models.ForeignKey(User)
    post = models.ForeignKey(PostModel)
    comment_text = models.CharField(max_length=200)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    has_upvoted = False

    @property
    def number_of_likes(self):
        return len(CommentLikeModel.objects.filter(comment=self))

class CommentLikeModel(models.Model):
    user = models.ForeignKey(User)
    comment = models.ForeignKey(CommentModel,null=True,blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on=models.DateTimeField(auto_now=True)




