import { EditorView } from './views/editor.js'
import { Overlay } from './views/components/overlay.js'
import { FeatureDetection } from './views/components/feature-detection.js'
import { Welcome } from './views/components/welcome.js'
import { store } from './store.js'
import { model } from './model.js'


function App(state, emit) {
  if (!('serial' in navigator)) {
    return html`
      <div id="app">
        ${EditorView(state, emit)}
        ${FeatureDetection(state, emit)}
      </div>`
  } else {
    return html`
      <div id="app">
        ${EditorView(state, emit)}
        ${Overlay(state, emit)}
        ${Welcome(state, emit)}
      </div>
    `
  }
}

let app = Choo()
app.use(model)
app.use(store)
app.route('*', App)
app.mount('#app')
