from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync
from couchpotato.core.helpers.request import getParams, jsonified
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie
from couchpotato.environment import Env
from urllib import urlencode


class MoviePlugin(Plugin):

    def __init__(self):
        addApiView('movie.search', self.search)
        addApiView('movie.list', self.list)
        addApiView('movie.refresh', self.refresh)

        addApiView('movie.add', self.add)
        addApiView('movie.edit', self.edit)
        addApiView('movie.delete', self.delete)

        path = self.registerStatic(__file__)
        fireEvent('register_script', path + 'search.js')
        fireEvent('register_style', path + 'search.css')
        fireEvent('register_script', path + 'movie.js')
        fireEvent('register_style', path + 'movie.css')
        fireEvent('register_script', path + 'list.js')

    def list(self):

        params = getParams()
        db = get_session()

        results = db.query(Movie).filter(
            Movie.status.has(identifier = params.get('status', 'active'))
        ).all()

        movies = []
        for movie in results:
            temp = movie.to_dict(deep = {
                'releases': {'status': {}, 'quality': {}, 'files':{}, 'info': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            })

            movies.append(temp)

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })

    def refresh(self):

        params = getParams()
        db = get_session()

        movie = db.query(Movie).filter_by(id = params.get('id')).first()

        # Get current selected title
        default_title = ''
        for title in movie.library.titles:
            if title.default: default_title = title.title

        if movie:
            #addEvent('library.update.after', )
            fireEventAsync('library.update', identifier = movie.library.identifier, default_title = default_title, force = True)
            fireEventAsync('searcher.single', movie.to_dict(deep = {
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}, 'files': {}, 'info': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            }))

        return jsonified({
            'success': True,
        })

    def search(self):

        params = getParams()
        cache_key = '%s/%s' % (__name__, urlencode(params))
        movies = Env.get('cache').get(cache_key)

        if not movies:
            results = fireEvent('provider.movie.search', q = params.get('q'))

            # Combine movie results
            movies = []
            for r in results:
                movies += r

            Env.get('cache').set(cache_key, movies)

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })

    def add(self):

        params = getParams()
        db = get_session();

        library = fireEvent('library.add', single = True, attrs = params)
        status = fireEvent('status.add', 'active', single = True)

        m = db.query(Movie).filter_by(library_id = library.get('id')).first()
        if not m:
            m = Movie(
                library_id = library.get('id'),
                profile_id = params.get('profile_id')
            )
            db.add(m)

        m.status_id = status.get('id')
        db.commit()

        movie_dict = m.to_dict(deep = {
            'releases': {'status': {}, 'quality': {}, 'files': {}, 'info': {}},
            'library': {'titles': {}}
        })

        return jsonified({
            'success': True,
            'added': True,
            'movie': movie_dict,
        })

    def edit(self):

        params = getParams()
        db = get_session();

        m = db.query(Movie).filter_by(id = params.get('id')).first()
        m.profile_id = params.get('profile_id')

        # Default title
        for title in m.library.titles:
            title.default = params.get('default_title').lower() == title.title.lower()

        db.commit()

        return jsonified({
            'success': True,
        })

    def delete(self):

        params = getParams()
        db = get_session()

        status = fireEvent('status.add', 'deleted', single = True)

        movie = db.query(Movie).filter_by(id = params.get('id')).first()
        movie.status_id = status.get('id')
        db.commit()

        return jsonified({
            'success': True,
        })
