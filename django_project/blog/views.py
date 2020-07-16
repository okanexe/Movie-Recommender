from django.shortcuts import render, get_object_or_404, redirect
from .models import Movies
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import authenticate
from users.models import Profile as pf
from users.forms import FileForm as fileform
import urllib

import pandas as pd
from itertools import combinations
from collections import Counter

import csv, io
from django.shortcuts import render
from django.contrib import messages

import os.path

#analiz sonucunda alınan kullanıcının keywordslerini sisteme yükler
def fileUpload(request):
    # eğer kullanıcı
    try:
        profile = request.user.profile
    except profile.DoesNotExist:
        profile = profile(user=request.user)

    if request.method == 'POST':
        form = fileform(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('blog-home')
    else:
        form = fileform(instance=profile)
    return render(request, 'blog/about.html', {'form':form})


#sisteme watchlisti yükler
def simple_upload(request):
    # user = request.user.is_authenticated
    us = True # kullanıcı profilinin açık olup olmadığını kontrol etmek için atandı
    try:
        if request.method == 'POST' and request.FILES['myfile']:
            if request.user.is_authenticated:  ## eğer hata olursa requesti üste and olarak al. şimdilik problem yok
                us = True
                myfile = request.FILES['myfile']
                if not myfile.name.endswith('.csv'): # dosya okunur .csv değilse uyarı verilir
                    messages.error(request, 'THIS IS NOT A CSV FILE')
                else:
                    fs = FileSystemStorage()
                    filename = fs.save(myfile.name, myfile)
                    uploaded_file_url = fs.url(filename)
                    """ "C:/Users/Ökans/Desktop/django_project/media/watchlist.csv" """
                    loc = fs.path(filename) #dosyanın bilgisayarda bulunan konumu döndürülür
                    a = pf.objects.get(pk=request.user.profile.id)
                    a.usersURL = loc
                    a.save()
                    # _, created = pf.objects.update(saveURL = loc)
                    return render(request, 'blog/simple_upload.html', {
                        'uploaded_file_url': uploaded_file_url,
                        'filename': loc,
                    })
            else:
                us = False # eğer false ise kullanıcı girişi yapılması istenecek
    except:
        messages.error(request, 'THIS IS NOT A CSV FILE')


    return render(request, 'blog/simple_upload.html',{'us':us})


#kullanıcı watchlistini analiz eder

def analysis(request):
    if request.method == 'POST':
        u = request.POST['urls']
        df = pd.read_csv(u, encoding='latin-1')
        df = df[["Title","IMDb Rating","Genres","Const"]] # kullanıcı watchlisti verilen kolon isimleri ile dataframe olarak oluşturulur.
        ## fetchdb(df) ## fetchdb analize yapacak ve word listesini geri döndürecek

        listem = comparison(df) # kullanıcının watchlistten gelen keywordslerini analiz edilmiş sonucunu tutar.
                                # önce comparison() fonksiyonuna gönderilir ve watchlist sistemdeli film dataseti ile eşlenir
                                # ardından sistemdeki datasetin "overview" kolonundan kullanıcının watchlisti ile eşleşen filmlerinin
                                # özetlerinden keywordser hesaplanır.Ardından gereksiz kelimeler çıkarılır.
                                # daha sonra en çok kullanılan kelimeler hesaplanarak ilk 30'u seçilerek döndürülür.

        usersGenres = usersKeysAnalysis(listem) # burada kullanıcının analiz edilen kelimeleri ile en çok ilgili olduğu film türleri
                                                # hesaplanır.
        # databasedeki dataset öneri için atanır
        dt = Movies.objects.values_list("imdb_id","title","overview","genre","IMDBScore")
        getAnalysis = pd.DataFrame.from_records(dt)
        getAnalysis.columns = ["imdb_id","title","overview","genre","IMDBScore"]

        # buradan dönen kullanıcıya önerilecek filmlerdir
        movie_list = recommenderList(df, getAnalysis, usersGenres)# df kullanıcının film listesi, getAnalysis olarak databasedeki
                                                                    # film datasetleri, userGenres olarak da kullanıcının ilgili olduğu
                                                                    # film türleri fonksiyona atanır.


        usersKeywordsList=[]
        for l in listem:
            usersKeywordsList.append(l)
        stringList = ' '.join([str(item) for item in usersKeywordsList])
        #sistemde kaydedebilmek için string olarak çeviriyoruz.
        #kullanıcının movieData alanını textField yaptığımız için

        #kullanıcı keywordslerini güncelliyor
        a = pf.objects.get(pk=request.user.profile.id)
        a.movieData = stringList
        a.save()

        return render(request, 'blog/reading.html', {
            'filename': df.Title,
            'listem': movie_list,
        })
    return render(request, 'blog/reading.html')




def fetchdb(request):
    dt = Movies.objects.values_list("imdb_id","overview")
    dataset = pd.DataFrame.from_records(dt)
    ##merging_id = dataset.merge(analysis, how='inner', left_on='Const', right_on='imdb_id')
    return render(request, 'blog/about.html', {
        'dataset': dataset[0]
    })

# kullanıcı watchlistini alıp sistemdeki dataset ile karşılaştırıp kelime analizi yapar
# en son bulunan kelimeleri hesaplayıp ilk 30 tanesini döndürmek için  usersKeywords() fonksiyonunu kullanır
def comparison(dataframe):
    dt = Movies.objects.values_list("imdb_id", "overview")
    dataset = pd.DataFrame.from_records(dt)
    dataset.columns = ["imdb_id", "overview"]

    analysis = dataset.merge(dataframe, how='inner', left_on="imdb_id", right_on='Const')
    analysis = analysis.dropna(how= 'any')
    keywords_list = []
    for row in analysis["overview"]:
        keywords = row.split(" ")
        for key in keywords:
            if (len(key) > 3):
                keywords_list.append(key)
    # analiz için gereksiz görülen kelimeler
    englishGrammar = ["with","that","from","their","they","into","when","When","must","this","have","after","only","find","will",
                "which","them","back","been","about","After","where","world","gets","film","while","himself","also",
                "over","being","become","becomes","through","other","between","most","whose","more","what","With","than",
                    "before","They","soon","house","just","some","finds","first","take","make","years"]
    # kullanıcı listesinde bulunan gereksiz kelimeler  silinir
    for i in englishGrammar:
        for j in keywords_list:
            if i == j:
                keywords_list.remove(j)
    return usersKeywords(keywords_list)

# kullanıcının kelime listesindeki en çok kullanılan kelimeleri döndürür
def usersKeywords(keywords_list):
    count = Counter()
    count.update(Counter(combinations(keywords_list, 1)))
    keys = []
    for key, value in count.most_common(30):
        keys.append(key)
    keys = [string_key for key in keys for string_key in key]
    return keys


def home(request):

    if request.method == 'POST':
        a = pf.objects.get(pk=request.user.profile.id)
        path = a.usersURL
        df = pd.read_csv(path, encoding='latin-1')
        df = df[["Title","IMDb Rating","Genres","Const"]] # kullanıcı watchlisti verilen kolon isimleri ile dataframe olarak oluşturulur.
        ## fetchdb(df) ## fetchdb analize yapacak ve word listesini geri döndürecek

        strlist = a.movieData
        listem = strlist.split(" ")


        usersGenres = usersKeysAnalysis(listem) # burada kullanıcının analiz edilen kelimeleri ile en çok ilgili olduğu film türleri
                                                # hesaplanır.
        # databasedeki dataset öneri için atanır
        dt = Movies.objects.values_list("imdb_id","title","overview","genre","IMDBScore")
        getAnalysis = pd.DataFrame.from_records(dt)
        getAnalysis.columns = ["imdb_id","title","overview","genre","IMDBScore"]

        # buradan dönen kullanıcıya önerilecek filmlerdir
        movie_list = recommenderList(df, getAnalysis, usersGenres)# df kullanıcının film listesi, getAnalysis olarak databasedeki
                                                                    # film datasetleri, userGenres olarak da kullanıcının ilgili olduğu
                                                                    # film türleri fonksiyona atanır.


        usersKeywordsList=[]
        for l in listem:
            usersKeywordsList.append(l)
        stringList = ' '.join([str(item) for item in usersKeywordsList])
        #sistemde kaydedebilmek için string olarak çeviriyoruz.
        #kullanıcının movieData alanını textField yaptığımız için

        #kullanıcı keywordslerini güncelliyor
        # a = pf.objects.get(pk=request.user.profile.id)
        # a.movieData = stringList
        # a.save()

        return render(request, 'blog/home.html', {
            'filename': movie_list,
        })
    return render(request, 'blog/home.html')



def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})


# cos_similarity() fonksiyonunu kullanarak belirlenen film türleri keywordleri ile tek tek karşılaştırılır.
# en yakın benzerliğe sahip 4 türü kullanıcının userGenres olarak atarız.

def usersKeysAnalysis(usersKeys):
    Biography = ['life', 'story', 'true', 'young', 'during', 'love', 'documentary', 'This', 'family', 'movie', 'Based',
                 'lives', 'early', 'career', 'time', 'famous', 'rise', 'John', 'father', 'tells', 'legendary',
                 'against',
                 'director', 'relationship', 'based', 'American', 'were', 'life,', 'made', 'music']

    Action = ['young', 'against', 'life', 'help', 'police', 'time', 'group', 'stop', 'story', 'love', 'save', 'evil',
              'team',
              'former', 'gang', 'takes', 'battle', 'down', 'fight', 'agent', 'named', 'death', 'mysterious', 'kill',
              'discovers', 'goes', 'mission', 'comes', 'during', 'family']

    Romance = ['love', 'young', 'life', 'woman', 'story', 'falls', 'meets', 'family', 'each', 'lives', 'girl',
               'friends',
               'relationship', 'both', 'mother', 'best', 'time', 'him.', 'takes', 'father', 'decides', 'begins',
               'wants',
               'living', 'goes', 'comes', 'life.', 'three', 'home', 'school']

    Musical = ['love', 'young', 'story', 'musical', 'family', 'life', 'falls', 'meets', 'married', 'named', 'three',
               'very',
               'daughter', 'This', 'girl', 'lives', 'live', 'woman', 'death', 'both', 'wife', 'father', 'marriage',
               'together',
               'takes', 'love.', 'time', 'him.', 'wealthy', 'comes']

    Animation = ['young', 'named', 'animated', 'save', 'time', 'story', 'life', 'help', 'evil', 'friends', 'girl',
                 'stop',
                 'family', 'adventure', 'mysterious', 'takes', 'Christmas', 'against', 'This', 'home', 'comes', 'away',
                 'city',
                 'tale', 'human', 'love', 'called', 'journey', 'him.', 'down']

    Thriller = ['young', 'life', 'woman', 'police', 'wife', 'group', 'takes', 'help', 'story', 'begins', 'goes',
                'murder',
                'down', 'family', 'time', 'people', 'lives', 'mysterious', 'love', 'then', 'death', 'home', "he's",
                'killer', 'small', 'town', 'against', 'former', 'discovers', 'kill']

    History = ['story', 'during', 'life', 'young', 'documentary', 'This', 'American', 'true', 'were', 'World',
               'against',
               'political', 'British', 'history', 'lives', 'love', 'Nazi', 'tells', 'group', 'events', 'German', 'team',
               'drama', 'movie', 'family', 'time', 'people', 'footage', 'military', 'would']

    Adventure = ['young', 'evil', 'life', 'help', 'against', 'story', 'save', 'family', 'named', 'time', 'mysterious',
                 'friends',
                 'adventure', 'group', 'stop', 'journey', 'father', 'discovers', 'discover', 'takes', 'three', 'battle',
                 'This',
                 'home', 'girl', 'secret', 'love', 'mission', 'friend', 'team']

    Sci_Fi = ['human', 'life', 'alien', 'time', 'group', 'stop', 'mysterious', 'young', 'help', 'people', 'scientist',
              'Earth',
              'team', 'year', 'deadly', 'planet', 'story', 'against', 'save', 'This', 'space', 'government', 'future',
              "he's",
              'former', 'small', 'evil', 'military', 'three', 'virus']

    Documentary = ['documentary', 'life', 'This', 'story', 'look', 'American', 'interviews', 'people', 'were',
                   'footage',
                   'music', 'many', 'Documentary', 'such', 'live', 'movie', 'made', 'follows', 'during', 'history',
                   'like',
                   'director', 'including', 'films', 'takes', 'three', 'time', 'York', 'filmmaker', 'work']

    Short = ['short', 'young', 'story', 'life', 'This', 'then', 'time', 'made', 'love', 'comes', 'people', 'girl',
             'woman',
             'many', 'tells', 'animated', 'there', 'film,', 'movie', 'images', 'small', 'music', 'around', 'down',
             'camera',
             'documentary', "it's", 'home', 'very', 'wants']

    Western = ['town', 'young', 'family', 'story', 'group', 'gold', 'former', 'outlaw', 'American', 'daughter', 'Call',
               'gang',
               'ranch', 'woman', 'brothers', 'Missie', 'Belinda', 'Wild', 'west', 'decide', 'save', 'Mexican', 'bounty',
               'beautiful', 'comes', 'legendary', 'head', 'life', 'until', 'returns']

    War = ['during', 'story', 'World', 'young', 'soldiers', 'American', 'group', 'British', 'Nazi', 'life', 'This',
           'family',
           'Jewish', 'German', 'were', 'war.', 'against', 'army', 'both', 'lives', 'U.S.', 'comes', 'Vietnam', 'tells',
           'military',
           'movie', 'soldier', 'fight', 'escape', 'takes']

    Mystery = ['young', 'woman', 'murder', 'life', 'mysterious', 'story', 'police', 'discovers', 'people', 'girl',
               'death', 'lives',
               'begins', 'killer', 'detective', 'wife', 'series', 'family', 'work', "he's", 'help', 'former', 'strange',
               'goes',
               'serial', 'takes', 'town', 'friend', 'husband', 'time']

    Comedy = ['life', 'young', 'love', 'family', 'story', 'help', 'woman', 'friends', 'time', 'comedy', 'lives', 'girl',
              'meets',
              'school', 'wants', 'best', 'each', 'takes', 'decides', 'friend', "he's", 'father', 'home', 'three',
              'local', 'town',
              'tries', 'falls', 'goes', 'This']

    Fantasy = ['young', 'life', 'love', 'evil', 'mysterious', 'story', 'time', 'help', 'girl', 'woman', 'family',
               'meets', 'named',
               'save', 'against', 'comes', 'takes', 'This', 'discovers', 'begins', 'lives', 'home', 'town', 'beautiful',
               'ancient',
               'stop', 'Christmas', 'each', 'father', 'people']

    Sport = ['team', 'story', 'football', 'life', 'school', 'coach', 'young', 'basketball', 'team.', 'player',
             'against', 'soccer',
             'high', 'star', 'former', 'game', 'players', 'baseball', 'American', 'hockey', 'play', 'follows', 'World',
             'college', 'returns', 'true', 'This', 'were', 'team,', 'lives']

    Family = ['young', 'family', 'help', 'life', 'father', 'named', 'story', 'girl', 'parents', 'Christmas', 'save',
              'home', 'school', 'friends', 'evil', 'time', 'love', 'discovers', 'little', 'mother', 'friend', 'wants',
              'town', 'comes', 'very', "he's", 'year', 'takes', 'This', 'away']

    Music = ['music', 'love', 'young', 'life', 'story', 'rock', 'band', 'musical', 'documentary', 'singer', 'This',
             'family',
             'time', 'lives', 'meets', 'woman', 'falls', 'group', 'live', 'girl', 'dance', 'together', 'takes', 'death',
             'both',
             'three', 'concert', 'school', 'many', 'movie']

    Adult = ['porn', 'Italian', 'theaters', 'hard', 'Holmes', 'thousands', 'sexual', 'several', 'island', 'Gothic',
             'horror',
             'tells', 'tale', 'stops', 'remote', 'castle', 'hoping', 'medical', 'help', 'injured', 'woman,',
             'inhabitants',
             'mirror', 'darker', 'sides', 'woman', 'himself.', "It's", 'hard,', 'year']

    Horror = ['young', 'group', 'woman', 'mysterious', 'begins', 'family', 'friends', 'town', 'life', 'killer', 'evil',
              'people', 'story', 'takes', 'girl', 'human', 'home', 'night', 'death', 'horror', 'time', 'school', 'then',
              'turns', 'strange', 'dead', 'begin', 'discover', 'killing', 'discovers']

    Crime = ['young', 'life', 'police', 'murder', 'story', 'crime', 'help', 'gang', 'takes', 'down', 'woman', 'money',
             'family', 'time', 'lives', 'drug', 'death', 'criminal', 'against', "he's", 'killer', 'love', 'detective',
             'goes',
             'local', 'him.', 'three', 'father', 'wants', 'wife']

    Drama = ['young', 'life', 'story', 'love', 'family', 'woman', 'lives', 'father', 'takes', 'girl', 'mother', 'wife',
             'time',
             'meets', 'friends', 'help', 'during', 'each', 'small', 'falls', 'This', 'school', 'begins', 'life.',
             'home', 'people',
             'three', 'town', 'decides', 'living']

    genres = [Action, Adult, Adventure, Animation, Biography, Comedy, Crime, Documentary, Drama, Family, Fantasy,
              History, Horror, Music, Musical, Mystery, Romance, Sci_Fi, Short, Sport, Thriller, War, Western]

    movieGenresDict = {'Action': {'data': Action, 'name': 'Action'}, 'Adult': {'data': Adult, 'name': 'Adult'},
                       'Adventure': {'data': Adventure, 'name': 'Adventure'},
                       'Animation': {'data': Animation, 'name': 'Animation'},
                       'Biography': {'data': Biography, 'name': 'Biography'},
                       'Comedy': {'data': Comedy, 'name': 'Comedy'},
                       'Crime': {'data': Crime, 'name': 'Crime'},
                       'Documentary': {'data': Documentary, 'name': 'Documentary'},
                       'Drama': {'data': Drama, 'name': 'Drama'}, 'Family': {'data': Family, 'name': 'Family'},
                       'Fantasy': {'data': Fantasy, 'name': 'Fantasy'}, 'History': {'data': History, 'name': 'History'},
                       'Horror': {'data': Horror, 'name': 'Horror'}, 'Music': {'data': Music, 'name': 'Music'},
                       'Musical': {'data': Musical, 'name': 'Musical'}, 'Mystery': {'data': Mystery, 'name': 'Mystery'},
                       'Romance': {'data': Romance, 'name': 'Romance'}, 'Sci_Fi': {'data': Sci_Fi, 'name': 'Sci_Fi'},
                       'Short': {'data': Short, 'name': 'Short'}, 'Sport': {'data': Sport, 'name': 'Sport'},
                       'Thriller': {'data': Thriller, 'name': 'Thriller'},
                       'War': {'data': War, 'name': 'War'}, 'Western': {'data': Western, 'name': 'Western'}}
    # movieGenreDict'e yeni bir özelllik olarak cos_similarity sonucu dönen benzerlikler eklenir.
    for item in movieGenresDict:
        movieGenresDict[item]['benzerlik'] = cos_similarity(usersKeys, movieGenresDict[item]['data'])

    inverse = [(value['benzerlik'], key) for key, value in movieGenresDict.items()]
    # burada en yüksek benzerliğe sahip türleri bulmak için sıralama yapılır
    for i in range(len(inverse)):

        min_idx = i
        for j in range(i + 1, len(inverse)):
            if (inverse[min_idx][0] > inverse[j][0]):
                min_idx = j

        inverse[i], inverse[min_idx] = inverse[min_idx], inverse[i]

    # en yüksek 4 tür userGenres'e atanır ve döndürülür.
    usersGenres = [i[1] for i in inverse[-4:]]

    return usersGenres
    # return inverse

# kullanıcnın film listesini, databasedeki film datasetini ve kullanıcının en ilgili 4 türü argüman olarak girilir.
def recommenderList(watchlist, getAnalysis, usersGenres):
    #benzer olan filmleri önermemek adına öneri listesinden düşürülür.
    cond = getAnalysis['imdb_id'].isin(watchlist['Const'])
    getAnalysis.drop(getAnalysis[cond].index, inplace=True)
    getAnalysis = getAnalysis.dropna(how='any')

    getAnalysis = getAnalysis[getAnalysis["IMDBScore"] > 7] # IMDB ratingi 7'nin altında olan filmler önerilmeyecek

    liste_3 = []
    liste_2 = []
    liste_1 = []
    liste_son = []
    for title, genres in zip(getAnalysis["title"], getAnalysis["genre"]):

        # genre türü database'de liste görünümlü string olarak kayıt edildiği için
        # burda tekrar liste haline getirdik.getAnalysis["genre"] içerisinde tür listeleri bulunmakta ama database'den
        # çektiğimizen dolayı string dönüyor bunu tekrar liste haline getirdik.
        index = 0
        gg = genres.split("'")
        i = 0
        genreList =[]
        for j in gg:
            if i % 2 == 1:
                genreList.append(j)
            i = i + 1
        # burada herhangi film türünden eşleşme sağlanırsa index 1 arttırılır.
        for genre in genreList:
            if genre == usersGenres[0]:
                index = index + 1
            if genre == usersGenres[1]:
                index = index + 1
            if genre == usersGenres[2]:
                index = index + 1
            if genre == usersGenres[3]:
                index = index + 1
        if index >= 3:
            liste_3.append(title)
        if index == 2:
            liste_2.append(title)
        if index == 1:
            liste_1.append(title)
    # index'i 1 arttırmamızın nedeni öncelikle fazla eşleşme olan filmleri öncelikli olarak sunabilmek.
    # alt kısımda da görüldüğü gibi öncelikle 3 eşleşme olan filmer ekleniyor.
    liste_son = liste_3[:5]

    if len(liste_son) < 20:
        for l in liste_2:
            liste_son.append(l)
            if len(liste_son) == 15:
                break
    if len(liste_son) < 20:
        for l in liste_1:
            liste_son.append(l)
            if len(liste_son) == 20:
                return liste_son

    return liste_son

# iki liste alıp listenin kelime benzerliğine göre cosine değeri bulur.
def cos_similarity(a, b):
    # word-lists to compare
    #a = [u'home (private)', u'bank', u'bank', u'building(condo/apartment)','factory']
    #b = [u'home (private)', u'school', u'bank', u'shopping mall']

    # count word occurrences
    a_vals = Counter(a)
    b_vals = Counter(b)

    # convert to word-vectors
    words  = list(a_vals.keys() | b_vals.keys())
    a_vect = [a_vals.get(word, 0) for word in words]        # [0, 0, 1, 1, 2, 1]
    b_vect = [b_vals.get(word, 0) for word in words]        # [1, 1, 1, 0, 1, 0]

    # find cosine
    len_a  = sum(av*av for av in a_vect) ** 0.5             # sqrt(7)
    len_b  = sum(bv*bv for bv in b_vect) ** 0.5             # sqrt(4)
    dot    = sum(av*bv for av,bv in zip(a_vect, b_vect))    # 3
    cosine = dot / (len_a * len_b)                          # 0.5669467
    return cosine
