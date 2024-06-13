from rest_framework import generics, status
from django.contrib.auth.models import User
from .serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
import pickle
import os

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class SignUpAPI(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def spotify_login(request):
    client_id = settings.SPOTIFY_CLIENT_ID
    redirect_uri = settings.SPOTIFY_REDIRECT_URI
    scope = 'user-read-private user-read-email'
    return redirect(f'https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}')

def spotify_callback(request):
    code = request.GET.get('code')
    client_id = settings.SPOTIFY_CLIENT_ID
    client_secret = settings.SPOTIFY_CLIENT_SECRET
    redirect_uri = settings.SPOTIFY_REDIRECT_URI

    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    }, verify=False)  # SSL 검증 비활성화

    try:
        response_data = response.json()
    except ValueError:
        print("Invalid response received from Spotify:")
        print(response.text)
        return JsonResponse({'error': 'Invalid response from Spotify'}, status=500)

    access_token = response_data.get('access_token')

    if not access_token:
        return JsonResponse({'error': 'Failed to retrieve access token from Spotify'}, status=400)

    user_info_response = requests.get('https://api.spotify.com/v1/me', headers={
        'Authorization': f'Bearer {access_token}'
    }, verify=False)  # SSL 검증 비활성화

    try:
        user_info = user_info_response.json()
    except ValueError:
        print("Invalid response received from Spotify API:")
        print(user_info_response.text)
        return JsonResponse({'error': 'Invalid response from Spotify API'}, status=500)

    return redirect('http://localhost:3000/diary?access_token=' + access_token)

class DiaryEntryAPI(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model_path = os.path.join(os.path.dirname(__file__), 'sentiment_model.pkl')
        vectorizer_path = os.path.join(os.path.dirname(__file__), 'vectorizer.pkl')
        label_encoder_path = os.path.join(os.path.dirname(__file__), 'label_encoder.pkl')
        
        with open(model_path, 'rb') as model_file:
            self.model = pickle.load(model_file)
        
        with open(vectorizer_path, 'rb') as vectorizer_file:
            self.vectorizer = pickle.load(vectorizer_file)
        
        with open(label_encoder_path, 'rb') as label_encoder_file:
            self.label_encoder = pickle.load(label_encoder_file)

    def post(self, request):
        text = request.data.get('text')
        if not text:
            return Response({'error': 'No text provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        text_vectorized = self.vectorizer.transform([text]).toarray()
        predicted_emotion_index = self.model.predict(text_vectorized)
        predicted_emotion = self.label_encoder.inverse_transform(predicted_emotion_index)
        
        return Response({'result': predicted_emotion[0]}, status=status.HTTP_200_OK)
