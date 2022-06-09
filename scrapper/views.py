from collections import Counter
import json
import re

import requests
from bs4 import BeautifulSoup
from django.http import HttpResponse
from django.shortcuts import render
import pandas as pd


# Create your views here.
def scrapper(request):
    searched = request.GET.get("s", "")
    movies = []
    movies = mobo(movies, searched)
    movies = digi(movies, searched)
    movies = set_order(movies, searched)
    jsonify = json.dumps(
        {"result": movies},
        ensure_ascii=False,
    )
    return HttpResponse(jsonify, content_type="application/json")


def latest_movies(request):
    searched = ""
    movies = []
    movies = mobo(movies, searched)
    movies = digi(movies, searched)
    movies = set_order(movies, searched)
    jsonify = json.dumps(
        {"result": movies[:10]},
        ensure_ascii=False,
    )
    return HttpResponse(jsonify, content_type="application/json")


def top_movies(request):
    movies = []
    movies = get_top_movies()
    data = {}
    data["result"] = movies[:7]
    jsonify = json.dumps(
        data,
        ensure_ascii=False,
    )
    return HttpResponse(jsonify, content_type="application/json")


def get_top_movies():
    url = f"https://digimovie.city/"
    movies = []
    try:
        page = requests.get(url)
        content = page.content
        soup = BeautifulSoup(content, "html.parser")
        movies_list = (
            soup.find(class_="index_slider")
                .find(class_="container")
                .find(class_="inner_index_slider")
        )
        if movies_list:
            for item in movies_list.find_all(class_="item_slider_index"):
                movie = {}
                title = item.find(class_="poster").find("a")["title"]
                movie["title"] = string_prettier(title)
                movie["default_img"] = "https://mobomovie1.xyz/img/default.png"
                movie["site"] = "https://digimovie.city"
                movie["rating"] = float(
                    string_prettier(
                        item.find(class_="poster_active")
                            .find(class_="left_side")
                            .find("strong")
                            .text
                    )
                )
                movie["image"] = item.find(class_="poster").find("a").find("img")["src"]
                movie["link"] = item.find(class_="poster").find("a")["href"]
                movie["extra_info"] = ""
                movies.append(movie)
    except Exception as e:
        raise e
    return movies


def string_prettier(string):
    string = string.strip()
    escapes = "".join([chr(char) for char in range(1, 32)])
    translator = str.maketrans("", "", escapes)
    string = string.translate(translator)
    without_space = re.sub(" +", " ", string)
    return without_space


def set_order(old_list, searched):
    def check_exist(arr1, arr2):
        result = False
        for item in arr1:
            if item in arr2:
                result = True
        return result

    def get_array(string):
        splitter = string.lower().split(" ")
        final = []
        for word in splitter:
            w_index = splitter.index(word)
            j = w_index + 1
            while j != len(splitter):
                final.append(" ".join(splitter[w_index: j + 1]))
                j += 1
        return final + splitter

    def start(searched_str):
        searched_str = searched_str.lower()
        result = []
        result_per = []
        for movie in old_list:
            title = " ".join(get_en_words(movie["title"])).lower()
            coms = get_array(title)
            if check_exist(searched_str.split(" "), coms):
                calculate(coms, movie, result, result_per, searched_str, title)
            else:
                result.append(movie)
                result_per.append(0)
        df = pd.DataFrame({"Movie": result, "Per": result_per})
        df = df.sort_values(by="Per", ascending=False)
        arr = df[["Movie"]].to_numpy()
        arr2 = [movie[0] for movie in arr]
        return arr2

    def calculate(coms, movie, result, result_per, searched_str, title):
        for com in coms:
            if com == searched_str:
                chopped = split_str(title, searched_str)
                n_chars = len(chopped)
                counter = Counter(chopped)
                occ_pct = {}
                for char, occ in counter.most_common():
                    occ_pct[char] = (occ / n_chars) * 100
                if searched_str in occ_pct:
                    result.append(movie)
                    searched_index = chopped.index(searched_str)
                    priority = occ_pct[searched_str] * (
                            (len(chopped) - searched_index) / len(chopped)
                    )
                    result_per.append(priority)

    def split_str(string, split_by):
        string = string.strip()
        string = string.split(" ")
        split_by_arr = split_by.split(" ")
        ded = []
        for item in string:
            if item not in split_by_arr:
                ded.append(item)
        ded.insert(string.index(split_by_arr[0]), split_by)
        return ded

    return start(searched)


def single(request):
    link = request.GET.get("link", "")
    if link.split("/")[2].strip() == "digimovie.city":
        return get_digi_single(link)
    elif link.split("/")[2].strip() == "mobomovie1.xyz":
        return get_mobo_single(link)


def get_digi_single(link):
    movie = {}
    try:
        page = requests.get(link)
        content = page.content
        soup = BeautifulSoup(content.decode('utf-8', 'ignore'), "html.parser")
        details = {}
        movie["actors"] = []
        movie["related"] = []
        for detail in soup.find(class_="single_meta_data").find("ul").find_all("li"):
            label = detail.find(class_="lab_item")
            value = detail.find(class_="res_item")
            details[string_prettier(label.text)] = string_prettier(value.text)
        movie['details'] = "__".join([f"{details[key]}_{key}" for key in details])
        story_tag = soup.find(class_="single_meta_data").find(class_="plot_text")
        movie["story"] = string_prettier(story_tag.text)
        for actor in soup.find(class_="cast_body").find_all(class_="item_cast"):
            name = actor.find(class_="actor_meta").find("h3")
            image = actor.find(class_="actor_image").find("img")["src"]
            together = {"name": string_prettier(name.text), "image": image}
            movie["actors"].append(together)
        for realated in soup.find(class_="related_posts").find_all(
                class_="item_small_loop"
        ):
            title = realated.find("a").find("h3")
            image = realated.find(class_="cover").find("img")
            link = realated.find("a")["href"]
            together = {
                "title": string_prettier(title.text),
                "image": image["src"],
                "link": link,
            }
            movie["related"].append(together)
            extra_info = []
        if soup.find(class_="subtitles_item"):
            extra_info.append("زیرنویس چسبیده")
        movie['extra_info'] = "__".join(extra_info)
        rating = soup.find(class_="imdb_holder_single").find("strong").text
        movie["rating"] = float(string_prettier(rating))
        return HttpResponse(json.dumps({"result": [movie]}, ensure_ascii=False), content_type="application/json")
    except Exception as e:
        jsonify = json.dumps({"error": "Something went wrong!"})
        #         raise(e)
        return HttpResponse(jsonify, content_type="application/json")


def get_mobo_single(link):
    movie = {}
    try:
        page = requests.get(link)
        content = page.content
        soup = BeautifulSoup(content.decode('utf-8', 'ignore'), "html.parser")
        details = {}
        movie["actors"] = []
        movie["related"] = []
        for detail in soup.find(class_="details").find("ul").find_all("li"):
            label = detail.find("h4")
            if label:
                value = detail.find("a")
                details[string_prettier(label.text)] = string_prettier(
                    value.text
                )
        movie['details'] = "__".join([f"{details[key]}_{key}" for key in details])
        story_tag = soup.find(class_="summary")
        story_tag.b.decompose()
        movie["story"] = string_prettier(story_tag.text)
        #         movie["story"] = story_tag.text
        for actor in soup.find(class_="cast").find_all(class_="cast-item"):
            name = actor.find("strong")
            image = actor.find("img")["data-src"]
            together = {"name": string_prettier(name.text), "image": image}
            movie["actors"].append(together)
        for realated in soup.find(id="movie-scroll").find_all(class_="scroll-item"):
            title = realated.find(class_="scroll-title")
            image = realated.find("img")
            link = realated.find("a")["href"]
            together = {
                "title": string_prettier(title.text),
                "image": image["src"],
                "link": link,
            }
            movie["related"].append(together)
            extra_info = []
        for extra in soup.find(class_="extra-info").find_all("p"):
            if extra.find(class_="check"):
                extra_info.append(string_prettier(extra.text))
        movie['extra_info'] = "__".join(extra_info)
        movie["rating"] = float(
            string_prettier(soup.find(class_="imdb-post").find_all("b")[0].text)
        )
        return HttpResponse(json.dumps({"result": [movie]}, ensure_ascii=False), content_type="application/json")
    except Exception as e:
        jsonify = json.dumps({"error": "Something went wrong!"})
        # raise (e)
        return HttpResponse(jsonify, content_type="application/json")


def get_en_words(string):
    list_words = []
    for word in string.strip().split(" "):
        check = re.match(r"[A-Za-z]", word)
        if check is not None:
            list_words.append(check.string.lower())
    return list_words


def mobo(movies, searched):
    url = f"https://mobomovie1.xyz/s/{searched}"
    try:
        page = requests.get(url)
        content = page.content
        soup = BeautifulSoup(content, "html.parser")
        movies_list = soup.find(class_="content-list")
        if movies_list:
            movies_list = movies_list.find(class_="content")
            for item in movies_list.find_all("article"):
                movie = {}
                title = item.find(class_="i-title").find("h2")
                movie["title"] = string_prettier(title.text)
                genres = []
                for genre in item.find(class_="item-genre").find_all("li"):
                    genres.append(string_prettier(genre.find("a").text))
                movie["genres"] = genres
                details = {}
                for detail in item.find(class_="item-details").find_all("li"):
                    label = detail.find("b")
                    value_list = detail.contents
                    value_list.remove(label)
                    value = ", ".join(
                        [
                            string_prettier(value.text) if value.text else None
                            for value in value_list
                        ]
                    )
                    details[string_prettier(label.text)] = value
                story_tag = item.find(class_="summary")
                movie["story"] = string_prettier(story_tag.text)
                extra = []
                for extra_info in item.find(class_="extra-info").find_all("p"):
                    if not extra_info.find(class_="fa-times"):
                        extra.append(string_prettier(extra_info.text))
                movie["details"] = details
                movie["extra_info"] = extra
                movie["default_img"] = "https://mobomovie1.xyz/img/default.png"
                movie["site"] = "https://mobomovie1.xyz"
                movie["image"] = item.find(class_="scroll-img")["data-src"]
                movie["link"] = item.find(class_="item-btn")["href"]
                movies.append(movie)
    except Exception as e:
        raise e
    return movies


def digi(movies, searched):
    url = f"https://digimovie.city/?s={searched}"
    try:
        page = requests.get(url)
        content = page.content
        soup = BeautifulSoup(content, "html.parser")
        movies_list = soup.find(class_="main_site")
        if movies_list:
            for item in movies_list.find_all(class_="item_def_loop"):
                movie = {}
                title = item.find(class_="title_h").find("a")
                movie["title"] = string_prettier(title.text)
                genres = ""
                details = {}
                for detail in item.find(class_="meta_item").find("ul").find_all("li"):
                    label = detail.find(class_="lab_item")
                    value = detail.find(class_="res_item")
                    if label is not None:
                        details[string_prettier(label.text)] = string_prettier(
                            value.text
                        )
                story_tag = item.find(class_="plot_text")
                movie["story"] = string_prettier(story_tag.text) if story_tag else ""
                extra = []
                if item.find(class_="subtitles_item"):
                    extra.append("زیرنویس چسبیده")
                movie["details"] = details
                movie["extra_info"] = "__".join(extra)
                movie["default_img"] = "https://mobomovie1.xyz/img/default.png"
                movie["site"] = "https://digimovie.city"
                movie["image"] = item.find(class_="attachment-poster_thumbnail")["src"]
                movie["link"] = item.find(class_="title_h").find("a")["href"]
                movies.append(movie)
    except Exception as e:
        raise e
    return movies


def home(request):
    return render(request, "scrapper/index.html")
