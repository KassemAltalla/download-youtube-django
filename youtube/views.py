import os
import json
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from yt_dlp import YoutubeDL
import time
import threading

downloads = {}  # قاموس لتتبع حالة التنزيلات

@csrf_exempt
@require_POST
def download_video(request):
    try:
        data = json.loads(request.body)
        video_url = data.get('video_url')  # يستخرج رابط الفيديو من الطلب المرسل
        if not video_url:
            return JsonResponse({'status': 'error', 'message': 'No video URL provided'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    task_id = str(time.time())  # معرف المهمة الفريد بناءً على الطابع الزمني
    ydl_opts = {
        'format': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]',  # أسوأ جودة فيديو مع أفضل جودة صوت
        'outtmpl': f'/tmp/{task_id}.%(ext)s',  # المسار الذي يتم تنزيل الفيديو إليه
        'merge_output_format': 'mp4',  # تحويل الفيديو إلى تنسيق mp4
        'progress_hooks': [lambda d: downloads.update({task_id: d})],  # تحديث حالة التنزيل
        'cookiefile': os.path.join(os.path.dirname(__file__), 'cookies.txt'),  # مسار ملف cookies.txt
    }

    downloads[task_id] = {'status': 'started', 'downloaded_bytes': 0, 'total_bytes': None, 'elapsed': 0}

    def download():
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)  # استخراج معلومات الفيديو وتنزيله
            video_file_path = ydl.prepare_filename(info_dict)  # مسار ملف الفيديو المحمّل
        downloads[task_id].update({'status': 'completed', 'video_file_path': video_file_path})

    threading.Thread(target=download).start()  # بدء عملية التنزيل في خط تنفيذ مستقل

    return JsonResponse({'task_id': task_id})  # إرجاع معرف المهمة كاستجابة

def get_download_status(request, task_id):
    if task_id not in downloads:
        return JsonResponse({'status': 'error', 'message': 'Invalid task ID'}, status=404)

    status = downloads[task_id]
    if status['status'] == 'completed':
        return JsonResponse({'status': 'completed', 'video_file_path': status['video_file_path']})

    if status['status'] == 'started' and status['total_bytes'] is not None:
        # حساب الوقت المقدر لاستكمال التنزيل
        downloaded_bytes = status['downloaded_bytes']
        total_bytes = status['total_bytes']
        elapsed = status['elapsed']
        remaining_bytes = total_bytes - downloaded_bytes
        speed = downloaded_bytes / elapsed if elapsed > 0 else 0
        eta_seconds = remaining_bytes / speed if speed > 0 else 0
        eta_minutes = eta_seconds / 60
        eta = f'{int(eta_minutes)} minutes' if eta_minutes < 60 else f'{int(eta_minutes / 60)} hours'
        status['eta'] = eta

    return JsonResponse(status)  # إرجاع حالة التنزيل كاستجابة JSON

def download_file(request, task_id):
    if task_id not in downloads or downloads[task_id]['status'] != 'completed':
        return JsonResponse({'status': 'error', 'message': 'File not available'}, status=404)
    
    video_file_path = downloads[task_id]['video_file_path']
    if not os.path.exists(video_file_path):
        return JsonResponse({'status': 'error', 'message': 'File not found'}, status=404)
    
    response = FileResponse(open(video_file_path, 'rb'), as_attachment=True, filename=os.path.basename(video_file_path))
    response['Content-Type'] = 'application/octet-stream'  # نوع المحتوى للملف المرسل
    response['Access-Control-Allow-Origin'] = '*'  # إعدادات CORS للسماح بالوصول من جميع المصادر
    return response