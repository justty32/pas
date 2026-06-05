/* md-browser.js — 可重用的 Markdown 文件樹瀏覽器（Web Component）
 *
 * 用法： <md-file-browser manifest="md-index.json" viewer="md.html"></md-file-browser>
 *   - manifest：.md 路徑清單 JSON（字串陣列），預設 md-index.json
 *   - viewer  ：檢視器頁面，預設 md.html（連結為 <viewer>?doc=<path>）
 *
 * 以原生 <details> 折疊資料夾，預設收合；提供「全展開／全收合」與分類快捷按鈕。
 * 純 light DOM，沿用 _shared.css 的 CSS 變數。
 */
class MdFileBrowser extends HTMLElement {
  connectedCallback() {
    this.manifest = this.getAttribute('manifest') || 'md-index.json';
    this.viewer = this.getAttribute('viewer') || 'md.html';
    this.innerHTML = '<div class="mdb-status">載入文件清單…</div>';
    fetch(this.manifest, { cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error(r.status + ' ' + r.statusText); return r.json(); })
      .then(paths => this.renderAll(paths))
      .catch(e => {
        this.innerHTML = '<div class="mdb-status mdb-err">無法載入文件清單 <code>' +
          this.manifest + '</code>：' + e.message + '</div>';
      });
  }

  // 由扁平路徑陣列建出巢狀樹
  buildTree(paths) {
    const root = { dirs: {}, files: [] };
    for (const p of paths) {
      const parts = p.split('/');
      let node = root;
      for (let i = 0; i < parts.length; i++) {
        if (i === parts.length - 1) {
          node.files.push({ name: parts[i], path: p });
        } else {
          node.dirs[parts[i]] = node.dirs[parts[i]] || { dirs: {}, files: [] };
          node = node.dirs[parts[i]];
        }
      }
    }
    return root;
  }

  countFiles(node) {
    let n = node.files.length;
    for (const k in node.dirs) n += this.countFiles(node.dirs[k]);
    return n;
  }

  esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

  // 遞迴產生樹的 HTML
  renderNode(node, openTop) {
    let html = '';
    for (const name of Object.keys(node.dirs).sort((a, b) => a.localeCompare(b))) {
      const child = node.dirs[name];
      const cnt = this.countFiles(child);
      html += '<details class="mdb-dir"' + (openTop ? ' open' : '') + '>' +
        '<summary>' + this.esc(name) + ' <span class="mdb-count">' + cnt + '</span></summary>' +
        '<div class="mdb-children">' + this.renderNode(child, false) + '</div>' +
        '</details>';
    }
    for (const f of node.files.sort((a, b) => a.name.localeCompare(b.name))) {
      const href = this.viewer + '?doc=' + encodeURIComponent(f.path);
      html += '<a class="mdb-file" href="' + href + '" title="' + this.esc(f.path) + '">' +
        this.esc(f.name) + '</a>';
    }
    return html;
  }

  renderAll(paths) {
    const tree = this.buildTree(paths);
    const total = paths.length;
    this.innerHTML =
      '<div class="mdb-toolbar">' +
        '<span class="mdb-total">' + total + ' 份 .md</span>' +
        '<span class="mdb-btns">' +
          '<button type="button" data-act="expand">全展開</button>' +
          '<button type="button" data-act="collapse">全收合</button>' +
        '</span>' +
      '</div>' +
      '<div class="mdb-tree">' + this.renderNode(tree, true) + '</div>';

    this.querySelector('[data-act="expand"]').addEventListener('click', () => {
      this.querySelectorAll('details.mdb-dir').forEach(d => d.open = true);
    });
    this.querySelector('[data-act="collapse"]').addEventListener('click', () => {
      this.querySelectorAll('details.mdb-dir').forEach(d => d.open = false);
    });
  }
}
customElements.define('md-file-browser', MdFileBrowser);
