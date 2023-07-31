import axios from 'axios'

const normalizeString = (str) => str.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')

const matchStringToKeyword = (s, keyword) => {
  return s && normalizeString(s).indexOf(keyword) >= 0
}

const matchSongVersionToKeyword = (song, keyword) => {
  if (matchStringToKeyword(song.title, keyword)) {
    return true
  }

  for (const a in song.authors) {
    if (matchStringToKeyword(a.name, keyword)) {
      return true
    }
  }

  return false
}

const matchSongToKeyword = (song, keyword) => {
  if (!song.versions) {
    return matchSongVersionToKeyword(song, keyword)
  }
  for (const i in song.versions) {
    if (matchSongVersionToKeyword(song.versions[i].song, keyword)) {
      return true
    }
  }
  return false
}

export default {
  state: {
    songs: [],
    searchKeyword: null,
    isLoaded: false,
  },
  mutations: {
    setSongs (state, songbook) {
      console.log('saving', songbook)
      state.songs = songbook['songs']
      for (let s = 0; s < state.songs.length; s++) {
        state.songs[s].index = s
        state.songs[s].author = state.songs[s].authors.join(', ')

        const blockIndex = {}
        for (let b = 0; b < state.songs[s].blocks.length; b++) {
          blockIndex[state.songs[s].blocks[b].name] = b
          if ('ref' in state.songs[s].blocks[b]) {
            state.songs[s].blocks[b].key = state.songs[s].blocks[b].name
            state.songs[s].blocks[b].lines = state.songs[s].blocks[blockIndex[state.songs[s].blocks[b].ref]].lines
            state.songs[s].blocks[b].name = state.songs[s].blocks[b].ref
          }
          if (state.songs[s].blocks[b].name.charAt(0) == '_') {
            state.songs[s].blocks[b].name = ""
          }
        }
      }

      console.log('updated  songs', state.songs)

      state.authors = songbook['authors']
      state.isLoaded = true
    },
    setSearchKeyword (state, payload) {
      state.searchKeyword = payload
    },
  },
  actions: {
    async loadSongs ({ commit }) {
      axios.get('https://raw.githubusercontent.com/marenamat/bratruv-zpevnik/uniformat/sbf/test.json')
        .then(response => {
          commit('setSongs', response.data['universal-songbook-format:songbook'])
        })
        .catch(error => {
          console.log(error)
        })
    },

  },
  getters: {
    songs: state => state.songs,
    filteredSongs: state => (
      state.searchKeyword && state.searchKeyword.length
        ? state.songs
          .filter(song => matchSongToKeyword(song, normalizeString(state.searchKeyword)))
        : state.songs
    ).map(song => song.versions ? { ...song.versions[0].song, index: song.index } : song),
    searchKeyword: state => state.searchKeyword,
    isLoaded: state => state.isLoaded,
    songsCount: state => state.songs.length,
  },
}
