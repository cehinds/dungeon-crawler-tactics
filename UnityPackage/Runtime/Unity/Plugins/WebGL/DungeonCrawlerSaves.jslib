// A user gesture invokes both functions from the Save / Load screen.
mergeInto(LibraryManager.library, {
  DCT_DownloadSave: function (jsonPointer) {
    var blob = new Blob([UTF8ToString(jsonPointer)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = 'dungeon-crawler-save.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  },
  DCT_ImportSave: function (objectPointer) {
    var objectName = UTF8ToString(objectPointer);
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.style.display = 'none';
    input.onchange = function () {
      var file = input.files && input.files[0];
      input.remove();
      if (!file) return;
      if (file.size > 1000000) {
        SendMessage(objectName, 'ReceiveSaveError', 'Choose a save JSON file under 1 MB.');
        return;
      }
      var reader = new FileReader();
      reader.onload = function () { SendMessage(objectName, 'ReceiveSaveJson', String(reader.result)); };
      reader.onerror = function () { SendMessage(objectName, 'ReceiveSaveError', 'The selected file could not be read.'); };
      reader.readAsText(file);
    };
    input.oncancel = function () { input.remove(); };
    document.body.appendChild(input);
    input.click();
  }
});
