(function(){
  var GUID = "7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801";
  try { host.FrameWork.ShowDialog(GUID); }
  catch (e) {
    try { host.FrameWork.ShowMessageBox("Corel AI Vector chua nap giao dien. Hay dong CorelDRAW, mo lai roi thu lai.\n\nLoi: " + (e.message || e.description || e), "Corel AI Vector"); } catch (ignore) {}
  }
})();
