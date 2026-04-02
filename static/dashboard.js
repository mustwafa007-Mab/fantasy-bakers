let contentState = {};

window.onload = async () => {
    // 1. Fetch CSRF token on load
    await refreshCsrf();

    // 2. Load Dashboard content
    const res = await fetch('/api/content');
    if (res.ok) {
        contentState = await res.json();
        document.getElementById('price-white-bread').value = contentState.price_product1 || '';
        document.getElementById('price-sugar-rolls').value = contentState.price_product2 || '';
        document.getElementById('price-buns').value = contentState.price_product3 || '';
        const m1 = document.getElementById('model-white-bread');
        const m2 = document.getElementById('model-sugar-rolls');
        const m3 = document.getElementById('model-buns');
        if (m1) m1.value = contentState.model_path_product1 || '';
        if (m2) m2.value = contentState.model_path_product2 || '';
        if (m3) m3.value = contentState.model_path_product3 || '';

        document.getElementById('vis-white-bread').checked = contentState.vis_product1 !== false;
        document.getElementById('vis-sugar-rolls').checked = contentState.vis_product2 !== false;
        document.getElementById('vis-buns').checked = contentState.vis_product3 !== false;
    }
};

async function refreshCsrf() {
    const res = await fetch('/admin/csrf-token', { credentials: 'include' });
    if (res.ok) {
        const data = await res.json();
        window.csrfToken = data.csrf_token;
        // Also populate the logout hidden field so the POST form has it
        const logoutField = document.getElementById('logout-csrf');
        if (logoutField) logoutField.value = data.csrf_token;
    }
}

function previewUpload(input, slot, isVideo = false) {
    const file = input.files[0];
    if (file) {
        const url = URL.createObjectURL(file);
        const span = document.getElementById(`preview-${slot}`);
        if (isVideo) {
            span.innerHTML = `<video style="height:50px; margin-left:10px; vertical-align:middle;" controls muted loop><source src="${url}"></video>`;
        } else {
            span.innerHTML = `<img src="${url}" style="height:50px; margin-left:10px; vertical-align:middle;">`;
        }
    }
}

async function uploadImage(formId, slot) {
    const form = document.getElementById(formId);
    const data = new FormData(form);
    const res = await fetch('/admin/upload_image', {
        method: 'POST',
        headers: {
            'x-csrf-token': window.csrfToken
        },
        body: data
    });
    if(res.ok) {
        alert(slot + ' uploaded successfully!');
        await refreshCsrf();
    } else {
        const err = await res.json();
        alert('Upload failed: ' + (err.detail || res.statusText));
    }
}

async function saveContent(key, value) {
    contentState[key] = value;
    const res = await fetch('/api/content', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'x-csrf-token': window.csrfToken
        },
        body: JSON.stringify(contentState)
    });
    if(res.ok) {
        // success silently or flash toast
        console.log(key + ' saved!');
        await refreshCsrf();
    } else {
        alert('Failed to save.');
    }
}
