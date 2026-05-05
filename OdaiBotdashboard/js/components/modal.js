const Modal = {
  show(title, bodyHTML, { confirmLabel = '保存', cancelLabel = 'キャンセル', onConfirm = null, onOpen = null, className = '' } = {}) {
    const container = document.getElementById('modal-container');
    container.innerHTML = `
      <div class="modal-overlay" id="modal-overlay">
        <div class="modal ${className}">
          <div class="modal__header">
            <h3 class="modal__title">${title}</h3>
            <button class="modal__close" id="modal-close">&times;</button>
          </div>
          <div class="modal__body">${bodyHTML}</div>
          ${onConfirm !== null ? `
          <div class="modal__footer">
            <button class="btn btn--ghost" id="modal-cancel">${cancelLabel}</button>
            <button class="btn btn--primary" id="modal-confirm">${confirmLabel}</button>
          </div>` : ''}
        </div>
      </div>
    `;
    document.getElementById('modal-close').addEventListener('click', () => this.close());
    document.getElementById('modal-overlay').addEventListener('click', e => {
      if (e.target === e.currentTarget) this.close();
    });
    if (onConfirm !== null) {
      document.getElementById('modal-cancel').addEventListener('click', () => this.close());
      document.getElementById('modal-confirm').addEventListener('click', onConfirm);
    }
    if (onOpen) onOpen();
  },
  close() {
    document.getElementById('modal-container').innerHTML = '';
  },
  confirm(title, message, onConfirm) {
    this.show(title, `<p class="modal__message">${message}</p>`, {
      confirmLabel: '削除',
      onConfirm: () => { onConfirm(); this.close(); },
    });
  },
};
