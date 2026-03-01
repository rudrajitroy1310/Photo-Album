import os
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Album, Photo
from .forms import UserRegisterForm, PhotoUploadForm
from django.contrib.auth.decorators import user_passes_test
from django.db import models
from django.http import FileResponse, Http404, StreamingHttpResponse
# Displays the list of all albums on the landing page
def album_list(request):
    query = request.GET.get('q') # <--- SEARCH IS BACK
    sort_by = request.GET.get('sort', 'date_new')

    # 1. First, apply the Search Filter
    if query:
        albums_qs = Album.objects.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query)
        ).distinct()
    else:
        albums_qs = Album.objects.all()

    # 2. Then, apply the Sorting
    if sort_by == 'name':
        albums = albums_qs.order_by('title')
    elif sort_by == 'date_old':
        albums = albums_qs.order_by('created_at')
    elif sort_by == 'items':
        albums = albums_qs.annotate(photo_count=models.Count('photos')).order_by('-photo_count')
    else:
        albums = albums_qs.order_by('-created_at')

    return render(request, 'gallery/album_list.html', {
        'albums': albums, 
        'current_sort': sort_by,
        'search_query': query # Passing this helps keep the search term in the box
    })

# Displays specific photos within a selected album
def album_detail(request, pk):
    album = get_object_or_404(Album, pk=pk)
    query = request.GET.get('q') # <--- SEARCH IS BACK
    sort_by = request.GET.get('sort', 'date_new')

    # 1. Filter by search query first
    if query:
        photos_qs = album.photos.filter(models.Q(caption__icontains=query))
    else:
        photos_qs = album.photos.all()

    # 2. Convert to list and apply Sorting
    photos = list(photos_qs)

    if sort_by == 'name':
        photos.sort(key=lambda x: x.caption.lower() if x.caption else "untitled")
    elif sort_by == 'date_old':
        photos.sort(key=lambda x: x.created_at)
    elif sort_by == 'date_new':
        photos.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == 'size':
        photos.sort(key=lambda x: x.image.size if x.image else 0, reverse=True)
    elif sort_by == 'type':
        photos.sort(key=lambda x: os.path.splitext(x.image.name)[1].lower())

    return render(request, 'gallery/album_detail.html', {
        'album': album, 
        'photos': photos, 
        'current_sort': sort_by,
        'search_query': query
    })
# ... (the rest of the bulk delete functions remain the same) ...

# Registration logic updated to create "Normal Users" only
def signin(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # --- NORMAL USER SETTINGS ---
            user.is_active = True  # Allows login
            user.is_staff = False  # Prevents access to the Django Admin panel
            user.is_superuser = False # Ensures they have no administrative power
            # ----------------------------
            
            user.save()
            
            # Log the user in right after registration
            login(request, user)
            
            # Redirect to 'home' (ensure name='home' exists in urls.py)
            return redirect('home')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def upload_photo(request):
    if request.method == 'POST':
        form = PhotoUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist('image')

        # 🔹 First validate the form
        if form.is_valid():
            # 🔹 Then validate files manually
            if not files:
                form.add_error('image', 'Please select at least one file.')
            else:
                album = form.cleaned_data['album']
                caption = form.cleaned_data['caption']

                for f in files:
                    Photo.objects.create(
                        album=album,
                        image=f,
                        caption=caption,
                        uploaded_by=request.user
                    )

                return redirect('album_detail', pk=album.id)
    else:
        form = PhotoUploadForm()

    return render(request, 'gallery/upload_photo.html', {'form': form})
def delete_photos_bulk(request):
    if request.method == 'POST':
        photo_ids = request.POST.getlist('photo_ids')
        album_id = request.POST.get('album_id')

        if 'confirm_delete' in request.POST:
            if photo_ids:
                # NEW STORAGE FEATURE: Get files to delete them from storage
                if request.user.is_superuser:
                    photos_to_wipe = Photo.objects.filter(id__in=photo_ids)
                else:
                    photos_to_wipe = Photo.objects.filter(id__in=photo_ids, uploaded_by=request.user)
                
                # Delete physical files
                for photo in photos_to_wipe:
                    if photo.image and os.path.isfile(photo.image.path):
                        os.remove(photo.image.path)
                
                # Delete database records
                photos_to_wipe.delete()
                
            return redirect('album_detail', pk=album_id)
        
        if photo_ids:
            photos_to_delete = Photo.objects.filter(id__in=photo_ids)
            return render(request, 'gallery/album_confirm_delete.html', {
                'photos': photos_to_delete,
                'photo_ids': photo_ids,
                'album_id': album_id,
                'type': 'photos'
            })
                
    return redirect('home')
@user_passes_test(lambda u: u.is_superuser)
def delete_albums_bulk(request):
    if request.method == 'POST':
        album_ids = request.POST.getlist('album_ids')

        if 'confirm_delete' in request.POST:
            if album_ids:
                # NEW STORAGE FEATURE: Delete cover images and all photos inside albums
                albums_to_wipe = Album.objects.filter(id__in=album_ids)
                
                for album in albums_to_wipe:
                    # 1. Delete Album Cover
                    if album.cover_image and os.path.isfile(album.cover_image.path):
                        os.remove(album.cover_image.path)
                    
                    # 2. Delete all Photos/Videos inside this album from storage
                    for photo in album.photos.all():
                        if photo.image and os.path.isfile(photo.image.path):
                            os.remove(photo.image.path)
                
                # 3. Finally delete the records from the database
                albums_to_wipe.delete()
                
            return redirect('home')

        if album_ids:
            albums_to_delete = Album.objects.filter(id__in=album_ids)
            return render(request, 'gallery/album_confirm_delete.html', {
                'albums': albums_to_delete,
                'album_ids': album_ids,
                'type': 'albums'
            })
                
    return redirect('home')


@login_required   # 🔥 THIS LINE IS THE KEY
def download_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)

    file_path = photo.image.path
    if not os.path.exists(file_path):
        raise Http404("File not found")

    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(file_path)
    )


def view_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    file_path = photo.image.path

    if not os.path.exists(file_path):
        raise Http404("File not found")

    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = "application/octet-stream"

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    def file_iterator(path, offset=0, length=None, chunk_size=8192):
        with open(path, "rb") as f:
            f.seek(offset)
            remaining = length
            while True:
                chunk = f.read(chunk_size if not remaining else min(chunk_size, remaining))
                if not chunk:
                    break
                yield chunk
                if remaining:
                    remaining -= len(chunk)
                    if remaining <= 0:
                        break

    if range_header:
        start, end = range_header.replace("bytes=", "").split("-")
        start = int(start)
        end = int(end) if end else file_size - 1
        length = end - start + 1

        response = StreamingHttpResponse(
            file_iterator(file_path, start, length),
            status=206,
            content_type=content_type,
        )
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Content-Length"] = str(length)
    else:
        response = StreamingHttpResponse(
            file_iterator(file_path),
            content_type=content_type,
        )
        response["Content-Length"] = str(file_size)

    response["Accept-Ranges"] = "bytes"
    return response

def view_album_cover(request, album_id):
    album = get_object_or_404(Album, id=album_id)

    if not album.cover_image:
        raise Http404("No cover image")

    file_path = album.cover_image.path
    content_type, _ = mimetypes.guess_type(file_path)

    if not content_type:
        content_type = "application/octet-stream"

    return FileResponse(
        open(file_path, "rb"),
        content_type=content_type
    )