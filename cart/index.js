// inspired by https://github.com/matthiask/workbench/tree/39a4287b45fc7a1b59a3eb9dfd9f11ef461c3834
// import "./index.css"

import ReactDOM from 'react-dom'
import React from 'react'
import { Provider } from 'react-redux'

// import {loadProjects} from "./actions.js"
import { configureStore } from './store.js'
import Cart from './Cart'

const storeInstance = configureStore()

document.addEventListener('DOMContentLoaded', () => {
  // loadProjects(storeInstance.dispatch)

  const el = document.querySelector('div#cart')
  ReactDOM.render(
    <Provider store={storeInstance}>
      <Cart/>
    </Provider>,
    el,
  )
})

