from django import forms
from models import User,PostModel,LikeModel,CommentModel,CommentLikeModel


class SignupForm(forms.ModelForm):
	class Meta:
		model=User
		fields=['email','name','username','password','parentmail']


class ProfileForm(forms.ModelForm):
	class Meta:
		model=User
		fields=['avatar']

class LoginForm(forms.ModelForm):
	class Meta:
		model=User
		fields=['username','password']

class PostForm(forms.ModelForm):
	class Meta:
		model=PostModel
		fields=['image','caption']

class StatusForm(forms.ModelForm):
	class Meta:
		model=User
		fields=['status']

class LikeForm(forms.ModelForm):
	class Meta:
		model=LikeModel
		fields=['post']


class CommentForm(forms.ModelForm):

    class Meta:
        model = CommentModel
        fields = ['comment_text', 'post']

class CommentLikeForm(forms.ModelForm):
	class Meta:
		model = CommentLikeModel
		fields = ['comment']

