let isTeraBoxConnected = false;

// Fungsi Aktivasi TeraBox
function activateTeraBox() {
    isTeraBoxConnected = true;
    document.getElementById('total-text').innerText = "1.015 TB";
    document.getElementById('bar-gdrive').style.width = "1.5%";
    document.getElementById('bar-terabox').style.width = "0%"; 
    
    const card = document.getElementById('terabox-card');
    card.className = "bg-emerald-600 p-6 rounded-3xl shadow-lg text-white flex flex-col justify-center items-center text-center";
    card.innerHTML = `<i class="fas fa-check-circle text-3xl mb-3"></i><h4 class="font-bold">TeraBox Terhubung</h4><p class="text-xs">1 TB Berhasil Ditambahkan</p>`;
    
    alert("Berhasil menghubungkan TeraBox via Google SSO!");
}

// Logika Drag and Drop & Deteksi File
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');

dropzone.onclick = () => fileInput.click();
fileInput.onchange = (e) => handleFiles(e.target.files);

function handleFiles(files) {
    const fileList = document.getElementById('file-list');
    
    Array.from(files).forEach(file => {
        let storageDestination = "";
        let iconColor = "";

        // Jika file > 500MB, arahkan ke TeraBox (jika sudah connect)
        if (file.size > 500 * 1024 * 1024) {
            if (!isTeraBoxConnected) {
                alert(`File "${file.name}" terlalu besar untuk Google Drive. Hubungkan TeraBox terlebih dahulu!`);
                return;
            }
            storageDestination = "TeraBox (1TB)";
            iconColor = "text-purple-500";
        } else {
            storageDestination = "Google Drive";
            iconColor = "text-blue-500";
        }

        const item = document.createElement('div');
        item.className = "bg-white p-4 rounded-2xl flex justify-between items-center shadow-sm border border-slate-100";
        item.innerHTML = `
            <div class="flex items-center gap-4">
                <i class="fas fa-file-alt ${iconColor} text-xl"></i>
                <div>
                    <p class="font-semibold text-slate-700">${file.name}</p>
                    <p class="text-xs text-slate-400 font-medium">${(file.size / (1024*1024)).toFixed(2)} MB</p>
                </div>
            </div>
            <span class="text-[10px] font-bold uppercase py-1 px-3 bg-slate-100 rounded-full text-slate-500">
                Tersimpan di: ${storageDestination}
            </span>
        `;
        fileList.prepend(item);
    });
}
