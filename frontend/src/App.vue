<template>
  <img alt="Vue logo" src="./assets/logo.png">
  <JuliyaNails msg="Welcome to JuliyaNails App"/>
</template>

<script>
import JuliyaNails from './components/JuliyaNails.vue'

export default {
  name: 'App',
  components: {
    JuliyaNails
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
