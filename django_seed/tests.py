from datetime import datetime
from faker import Faker
from django_seed.seeder import Seeder
from django_seed.exceptions import SeederException, SeederCommandError
from django_seed import Seed

import random
import django

from django.db import models
try:
    from django.utils.unittest import TestCase
except:
    from django.test import TestCase
from django.core.management import call_command


fake = Faker()


class Game(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_date = models.DateField()
    updated_time = models.TimeField()
    active = models.BooleanField()
    max_score = models.BigIntegerField()
    levels = models.SmallIntegerField()
    likes = models.IntegerField()
    random_binary = models.BinaryField()


class Player(models.Model):
    nickname = models.CharField(max_length=100)
    tagline = models.CharField(max_length=128)
    avatar = models.FilePathField()
    score = models.BigIntegerField()
    last_login_at = models.DateTimeField()
    game = models.ForeignKey(Game)
    ip = models.IPAddressField()
    achievements = models.CommaSeparatedIntegerField(max_length=1000)
    friends = models.PositiveIntegerField()
    balance = models.FloatField()


class Action(models.Model):
    ACTION_FIRE ='fire'
    ACTION_MOVE ='move'
    ACTION_STOP ='stop'
    ACTIONS = (
        (ACTION_FIRE,'Fire'),
        (ACTION_MOVE,'Move'),
        (ACTION_STOP,'Stop'),
    )
    name = models.CharField(max_length=4, choices=ACTIONS)
    executed_at = models.DateTimeField()
    if django.VERSION[1] >= 8:
        duration = models.DurationField()
        uuid = models.UUIDField()
    actor = models.ForeignKey(Player,related_name='actions', null=False)
    target = models.ForeignKey(Player, related_name='enemy_actions+', null=True)


class SeederTestCase(TestCase):

    def test_population(self):
        faker = fake
        seeder = Seeder(faker)
        seeder.add_entity(Game, 10)
        self.assertEqual(len(seeder.execute()[Game]), 10)

    def test_guesser(self):
        faker = fake
        def title_fake(arg):
            title_fake.count += 1
            name = faker.company()
            return name
        title_fake.count = 0
        seeder = Seeder(faker)
        seeder.add_entity(Game, 10, {
            'title': title_fake
        })
        self.assertEqual(len(seeder.execute()[Game]), title_fake.count)

    def test_timezone(self):
        """test if datetime objects are created timezone aware
        based on USE_TZ in settings.py
        """
        faker = fake
        seeder = Seeder(faker)
        try:
            # import django settings
            from django.conf import settings
            from django.utils import timezone
        except ImportError:
            pass
        # check if timezone is active
        if not getattr(settings, 'USE_TZ', False):
            setattr(settings, 'USE_TZ', True)
            deactivate_tz = True
        else:
            deactivate_tz = False
        seeder.add_entity(Game, 1)
        game = Game.objects.get(pk=seeder.execute()[Game][0])
        if deactivate_tz:
            # reset timezone settings
            setattr(settings, 'USE_TZ', False)
        self.assertTrue(timezone.is_aware(game.created_at))

    def valid_player(self, player):
        p = player
        return 0 <= p.score <= 1000 and '@' in p.nickname

    def test_formatter(self):
        faker = fake
        seeder = Seeder(faker)
        seeder.add_entity(Game,5)
        seeder.add_entity(Player, 10, {
            'score': lambda x: random.randint(0,1000),
            'nickname': lambda x: fake.email()
        })
        seeder.add_entity(Action,30)
        inserted_pks = seeder.execute()
        self.assertTrue(len(inserted_pks[Game]) == 5)
        self.assertTrue(len(inserted_pks[Player]) == 10)

        players = Player.objects.all()
        self.assertTrue(any([self.valid_player(p) for p in players]))

    def test_null_foreign_key(self):
        faker = fake
        seeder = Seeder(faker)
        try:
            seeder.add_entity(Action, 1)
            seeder.execute()
        except Exception as e:
            self.assertTrue(isinstance(e, SeederException))
        pass

    def test_no_entities_added(self):
        faker = fake
        seeder = Seeder(faker)
        try:
            seeder.execute()
        except Exception as e:
            self.assertTrue(isinstance(e, SeederException))

    def test_auto_now_add(self):
        date =  datetime(1957, 3, 6, 13, 13)
        faker = fake
        seeder = Seeder(faker)
        seeder.add_entity(Game, 10, {
            'created_at': lambda x: date
        })
        inserted_pks = seeder.execute()[Game]

        games = Game.objects.filter(pk__in=inserted_pks)
        self.assertTrue(all(game.created_at == date for game in games))

    def test_auto_now(self):
        date =  datetime(1957, 3, 6, 13, 13)
        faker = fake
        seeder = Seeder(faker)
        seeder.add_entity(Game, 10, {
            'updated_at': lambda x: date
        })
        inserted_pks = seeder.execute()[Game]

        games = Game.objects.filter(pk__in=inserted_pks)
        self.assertTrue(all(game.updated_at == date for game in games))


class APISeedTestCase(TestCase):

    def setUp(self):
        self.seed1 = Seed()
        self.seed2 = Seed()

    def test_django_seed_singleton(self):
        self.assertEqual(self.seed1, self.seed2)
        self.assertIs(self.seed1, self.seed1)

    def test_faker_cache_faker(self):
        gen1 = self.seed1.faker()
        gen2 = self.seed2.faker()
        self.assertIs(gen1, gen2)

        gen1 = self.seed1.faker(codename='default')
        gen2 = self.seed2.faker(codename='default')
        self.assertIs(gen1, gen2)

        gen1 = self.seed1.faker(locale='it_IT')
        gen2 = self.seed2.faker(locale='it_IT')
        self.assertIs(gen1, gen2)

    def test_faker_cache_seeder(self):
        seeder1 = self.seed1.seeder()
        seeder2 = self.seed2.seeder()
        self.assertIs(seeder1, seeder2)

        gen1 = seeder1.faker
        gen2 = seeder2.faker
        self.assertIs(gen1, gen2)

        seeder1 = self.seed1.seeder(locale='it_IT')
        seeder2 = self.seed2.seeder(locale='it_IT')
        self.assertIs(seeder1, seeder2)


class SeedCommandTestCase(TestCase):

    def test_seed_command(self):
        call_command('seed', 'django_seed', number=10)

    def test_invalid_number_arg(self):
        try:
            call_command('seed', 'django_seed', number='asdf')
        except Exception as e:
            self.assertTrue(isinstance(e, SeederCommandError))
        pass
