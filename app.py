javascript:(function(){try{
    var titleEl = document.querySelector('h1') || document.querySelector('title');
    var title = titleEl ? titleEl.innerText.split('|')[0].trim() : '';

    var cinema = '';
    var cinemaEl = document.querySelector('[class*="Cinema"], [class*="cinema"], h2');
    if (cinemaEl) { cinema = cinemaEl.innerText.trim(); }

    // Look for times matching "20h00" or "20:00" on the page
    var time = '20:00';
    var selectedSlot = document.querySelector('[class*="Selected"], [class*="selected"], [class*="active"]');
    var targetText = selectedSlot ? selectedSlot.innerText : document.body.innerText;
    
    var timeMatch = targetText.match(/\b([01]?\d|2[0-3])[:h]([0-5]\d)\b/i);
    if (timeMatch) {
        time = timeMatch[1].padStart(2, '0') + ':' + timeMatch[2];
    }

    var date = new Date().toISOString().split('T')[0];
    var dateMatch = document.body.innerText.match(/\b\d{4}-\d{2}-\d{2}\b/);
    if (dateMatch) date = dateMatch[0];

    var synopsis = '';
    var synopsisEl = document.querySelector('[class*="FilmSynopsis"]') || document.querySelector('.synopsis, p.description');
    if (synopsisEl) { synopsis = synopsisEl.innerText.trim(); }

    var url = window.location.href;
    var target = "https://paris-film-radar-lqd7tb9rcb84kdnmh9z5hp.streamlit.app/?title=" + encodeURIComponent(title) + "&cinema=" + encodeURIComponent(cinema) + "&date=" + encodeURIComponent(date) + "&time=" + encodeURIComponent(time) + "&url=" + encodeURIComponent(url) + "&synopsis=" + encodeURIComponent(synopsis.substring(0, 600));

    window.location.assign(target);
}catch(e){alert('Error importing: ' + e.message);}})();
